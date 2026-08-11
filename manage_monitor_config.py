#!/usr/bin/env python3
import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path("monitor_config.json")
STATE_PATH = Path("monitor_state.json")


def load_json(path):
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_match_mode(value):
    if not value:
        return "both"
    v = value.strip().lower()
    choices = {"appearance", "disappearance", "both"}
    mapping = {"出現": "appearance", "消失": "disappearance", "両方": "both"}
    if v in mapping:
        return mapping[v]
    if v in choices:
        return v
    raise ValueError(
        "match_mode must be one of: appearance/出現, disappearance/消失, both/両方"
    )


def slugify(value):
    # kept for backward-compatibility but not used for numeric ids
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"(^-|-$)", "", value)
    return value or "target"


def generate_next_integer_id(targets):
    # Find numeric ids among existing targets and return next integer id
    max_id = 0
    for t in targets:
        tid = t.get("id")
        try:
            n = int(tid)
            if n > max_id:
                max_id = n
        except Exception:
            continue
    return max_id + 1


def add_target(args):
    config = load_json(args.config)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid config format: {args.config}")
    targets = config.get("targets")
    if targets is None:
        targets = []
        config["targets"] = targets
    elif not isinstance(targets, list):
        raise ValueError(f"Invalid targets format in {args.config}")

    match_mode = normalize_match_mode(args.match_mode)
    frequency_minutes = int(args.frequency_minutes) if args.frequency_minutes else 15
    if frequency_minutes < 0:
        raise ValueError("frequency_minutes must be 0 or greater")

    # verify the URL is reachable (HEAD preferred, fallback to GET)
    def _check_url(u):
        req = urllib.request.Request(u, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True
        except urllib.error.HTTPError as he:
            # Some servers disallow HEAD; try GET as fallback
            if he.code == 405:
                try:
                    with urllib.request.urlopen(u, timeout=10) as r2:
                        return True
                except Exception as e:
                    raise ValueError(f"URL is not reachable: {u} ({e})")
            raise ValueError(f"URL returned HTTP error: {u} ({he.code})")
        except Exception as e:
            raise ValueError(f"URL is not reachable: {u} ({e})")

    # attempt URL check
    try:
        _check_url(args.url)
    except Exception as exc:
        raise ValueError(f"Failed to reach URL '{args.url}': {exc}")

    # generate integer auto-increment id
    target_id = generate_next_integer_id(targets)

    new_target = {
        "id": target_id,
        "name": args.name,
        "url": args.url,
        "pattern_type": "text",
        "pattern": args.pattern or "",
        "match_mode": match_mode,
        "frequency_minutes": frequency_minutes,
    }
    targets.append(new_target)
    save_json(args.config, config)
    print(f"Added monitoring target: {target_id}")


def remove_target(args):
    config = load_json(args.config)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid config format: {args.config}")
    targets = config.get("targets")
    if not isinstance(targets, list):
        raise ValueError(f"Invalid targets format in {args.config}")

    original_length = len(targets)
    # allow numeric or string id input
    id_param = args.id
    try:
        id_int = int(id_param)
    except Exception:
        id_int = None

    def id_matches(t):
        tid = t.get("id")
        if tid is None:
            return False
        if id_int is not None:
            try:
                return int(tid) == id_int
            except Exception:
                return str(tid) == str(id_param)
        return str(tid) == str(id_param)

    targets = [t for t in targets if not id_matches(t)]
    if len(targets) == original_length:
        raise ValueError(f"No target with id '{args.id}' found in {args.config}")
    config["targets"] = targets
    save_json(args.config, config)

    state = load_json(args.state)
    if isinstance(state, dict):
        removed = False
        # remove both string and numeric keys if present
        if id_param in state:
            del state[id_param]
            removed = True
        if id_int is not None and str(id_int) in state:
            del state[str(id_int)]
            removed = True
        if removed:
            save_json(args.state, state)
            print(f"Removed state for target: {args.id}")
    else:
        print(f"No state entry found for target: {args.id}")

    print(f"Removed monitoring target: {args.id}")


def parse_args():
    parser = argparse.ArgumentParser(description="Manage monitor_config.json and monitor_state.json")
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="monitor_config.json path",
    )
    parser.add_argument(
        "--state",
        default=str(STATE_PATH),
        help="monitor_state.json path",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a monitoring target")
    add_parser.add_argument("--name", required=True, help="監視対象名")
    add_parser.add_argument("--url", required=True, help="監視対象URL")
    add_parser.add_argument(
        "--match-mode",
        default="both",
        help="判定モード: appearance/出現, disappearance/消失, both/両方",
    )
    add_parser.add_argument("--pattern", default="", help="監視パターン")
    add_parser.add_argument(
        "--frequency-minutes",
        default="15",
        help="監視頻度（分）",
    )

    remove_parser = subparsers.add_parser("remove", help="Remove a monitoring target by id")
    remove_parser.add_argument("--id", required=True, help="監視対象のID")

    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "add":
        add_target(args)
    elif args.command == "remove":
        remove_target(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
