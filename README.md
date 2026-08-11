# website-state-notificator

ローカルでのテスト手順と設定ファイルを以下に記載します。

## ローカル実行準備

1. リポジトリをクローンしてワークスペースに移動します。
2. `.env.example` をコピーして `.env` を作成し、LINEのチャネルIDとチャネルシークレットを設定します。

```powershell
copy .env.example .env
# `.env` の内容を編集して LINE_CHANNEL_ID と LINE_CHANNEL_SECRET を設定します
```

## 依存関係

このリポジトリは標準の Python 標準ライブラリのみを使用します。

## 実行方法

```powershell
python monitor.py --env-file .env
```

### オプション

- `--config` / `-c`: 監視設定ファイル（デフォルト: `monitor_config.json`）
- `--state` / `-s`: 状態保存ファイル（デフォルト: `monitor_state.json`）
- `--env-file` / `-e`: 環境変数ファイル（デフォルト: `.env`）
- `--dry-run` / `-n`: LINE通知を送信せず、検出結果のみ表示します

## ドライラン例

```powershell
python monitor.py --env-file .env --dry-run
```

## テスト用設定

`monitor_config.json` に監視対象と判定ルールを記載し、必要に応じて `line_recipient` を設定してください。
