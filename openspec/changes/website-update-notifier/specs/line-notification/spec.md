## ADDED Requirements

### Requirement: Send LINE notifications for detected changes
システムは、監視対象URLの判定ルールが変化したときに、設定された各LINE通知先にメッセージを送信しなければならない。

#### Scenario: Notification message on rule change
- **WHEN** 監視対象ページの判定ルールが出現/消失の変化によりトリガーされたとき
- **THEN** システムはURL、判定ルール、および検出された状態変化を説明するLINEメッセージをすべての設定通知先に送信する

### Requirement: LINE message contents must clearly identify the event
システムは、LINE通知に監視対象のURL、判定ルール、以前の状態、および現在の状態を含めなければならない。

#### Scenario: Message includes change details
- **WHEN** 変更通知メッセージが生成されるとき
- **THEN** メッセージ本文には監視対象のURL、判定ルール、および変更前後でパターンが一致していたかどうかが含まれる

### Requirement: Use LINE Messaging API for delivery
システムは、LINE Messaging APIを使用して通知を送信し、アクセストークンなどの認証情報を安全に管理しなければならない。

#### Scenario: Configure LINE API settings
- **WHEN** LINE APIのアクセストークンと通知先設定が提供されるとき
- **THEN** システムはそれらを使ってLINEメッセージを送信できる
