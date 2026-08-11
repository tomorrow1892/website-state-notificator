#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

CONFIG_PATH = "monitor_config.json"
STATE_PATH = "monitor_state.json"
LINE_PUSH_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_BROADCAST_API_URL = "https://api.line.me/v2/bot/message/broadcast"
LINE_OAUTH_TOKEN_URL = "https://api.line.me/v2/oauth/accessToken"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_env_file(path):
    if not path or not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Website state monitor for LINE notifications"
    )
    parser.add_argument(
        "--config",
        "-c",
        default=CONFIG_PATH,
        help="監視設定JSONファイルのパス",
    )
    parser.add_argument(
        "--state",
        "-s",
        default=STATE_PATH,
        help="状態保存JSONファイルのパス",
    )
    parser.add_argument(
        "--env-file",
        "-e",
        default=".env",
        help="環境変数ファイルのパス（存在しない場合は無視されます）",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="LINE送信を行わず、検出結果のみ表示します",
    )
    return parser.parse_args()


def fetch_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WebsiteStateNotifier/1.0; +https://github.com/)"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def evaluate_pattern(content, target):
    pattern_type = target.get("pattern_type", "text")
    pattern = target.get("pattern", "")
    if pattern_type == "regex":
        return bool(re.search(pattern, content, re.MULTILINE))
    return pattern in content


def parse_iso_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


JST = timezone(timedelta(hours=9))

def format_timestamp(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).replace(microsecond=0).isoformat()


def should_check(target, state_entry):
    frequency = int(target.get("frequency_minutes", 15))
    if frequency <= 0:
        return True
    if not state_entry or not state_entry.get("last_checked"):
        return True
    last_checked = parse_iso_timestamp(state_entry.get("last_checked"))
    if not last_checked:
        return True
    return datetime.now(timezone.utc) - last_checked >= timedelta(minutes=frequency)


def build_line_message(target, previous_match, current_match, content):
    status_map = {True: "あり", False: "なし"}
    pattern = target.get("pattern", "")
    name = target.get("name") or target.get("id") or target.get("url")

    if previous_match is True and current_match is False:
        mode_label = "消えちゃったホイ…"
    elif previous_match is False and current_match is True:
        mode_label = "見つけたホイ！"
    else:
        mode_label = "状況が変わったホイ！"

    description = (
        f"フク助だホイ🦉\n"
        f"ページが更新されたホイな～\n\n"
        f"対象名: {name}\n"
        f"URL: {target.get('url')}\n"
        f"判定: {mode_label}\n"
        f"監視パターン: 「{pattern}」\n"
        f"検出時刻: {format_timestamp(datetime.now(JST))}\n\n"
    )
    return description


def get_line_access_token(channel_id, channel_secret):
    if not channel_id or not channel_secret:
        return None
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": channel_id,
            "client_secret": channel_secret,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        LINE_OAUTH_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
            return payload.get("access_token")
    except urllib.error.HTTPError as exc:
        print(f"LINEアクセストークン取得失敗: {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        print(f"LINEアクセストークン取得失敗: {exc}")
    return None


def send_line_message(token, recipient_id, message_text):
    if not token:
        raise ValueError("LINE access token is not available")
    payload = {
        "messages": [
            {
                "type": "text",
                "text": message_text,
            }
        ],
    }
    if recipient_id:
        payload["to"] = recipient_id
        url = LINE_PUSH_API_URL
    else:
        url = LINE_BROADCAST_API_URL

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LINE API HTTP {exc.code}: {body}") from exc


def main(args):
    load_env_file(args.env_file)

    config = load_json(args.config)
    if not config or "targets" not in config:
        print(f"設定ファイルが見つからないか、targetsキーがありません: {args.config}")
        return 0

    channel_id = os.getenv("LINE_CHANNEL_ID")
    channel_secret = os.getenv("LINE_CHANNEL_SECRET")
    line_access_token = None
    if not args.dry_run:
        line_access_token = get_line_access_token(channel_id, channel_secret)
        if not line_access_token:
            print(
                "環境変数LINE_CHANNEL_IDまたはLINE_CHANNEL_SECRETが設定されていないか、アクセストークンの取得に失敗しました。LINE通知は送信できません。"
            )
    else:
        print("DRY RUN: LINE通知は送信されません。検出結果のみ表示します。")

    state = load_json(args.state)
    targets = config.get("targets", [])
    updated_state = state.copy()
    any_notifications = False
    failed_targets = []

    for target in targets:
        raw_id = target.get("id") or target.get("url")
        target_key = str(raw_id)
        if not raw_id or not target.get("url"):
            print(f"スキップ: idまたはurlが指定されていない監視対象: {target}")
            continue

        previous = updated_state.get(target_key, {})
        entry = previous.copy()
        checked = should_check(target, previous)
        if not checked:
            print(f"スキップ: {target_id} はまだ実行頻度に達していません。")
            continue

        print(f"チェック開始: {target_id} ({target.get('url')})")
        page_content = None
        try:
            page_content = fetch_url(target["url"])
        except urllib.error.URLError as exc:
            print(f"URL取得失敗: {target_id} - {exc}")
            failed_targets.append(raw_id)
            entry["last_checked"] = format_timestamp(datetime.now(timezone.utc))
            updated_state[target_key] = entry
            continue

        current_match = evaluate_pattern(page_content, target)
        previous_match = previous.get("last_match")
        match_mode = target.get("match_mode", "both")
        should_notify = False

        if previous_match is not None:
            if match_mode in {"appearance", "both"}:
                if not previous_match and current_match:
                    should_notify = True
            if match_mode in {"disappearance", "both"}:
                if previous_match and not current_match:
                    should_notify = True

        entry["last_checked"] = format_timestamp(datetime.now(timezone.utc))
        entry["last_match"] = current_match
        updated_state[target_key] = entry

        if should_notify:
            recipient = target.get("line_recipient") or config.get("line_recipient")
            if not line_access_token:
                print(f"LINEアクセストークンが取得できません: {target_id}")
            else:
                message = build_line_message(target, previous_match, current_match, page_content)
                try:
                    result = send_line_message(line_access_token, recipient, message)
                    if recipient:
                        print(f"LINE通知送信完了: {target_id} -> {recipient}")
                    else:
                        print(f"LINEブロードキャスト送信完了: {target_id}")
                    any_notifications = True
                except Exception as exc:
                    if recipient:
                        print(f"LINE通知送信失敗: {target_id} -> {recipient} : {exc}")
                    else:
                        print(f"LINEブロードキャスト送信失敗: {target_id} : {exc}")
                    failed_targets.append(target_id)
        else:
            print(f"通知なし: {target_id} (前回={previous_match}, 今回={current_match})")

    if updated_state != state:
        save_json(args.state, updated_state)
        print(f"状態を保存しました: {args.state}")
    else:
        print("状態に変更はありませんでした。")

    if failed_targets:
        print(f"失敗した監視対象: {', '.join(sorted(set(failed_targets)))}")
        return 1

    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args))
