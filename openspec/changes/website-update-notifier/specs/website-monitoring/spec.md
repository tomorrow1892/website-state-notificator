## ADDED Requirements

### Requirement: Support multiple monitoring targets and recipients
システムは、複数の監視対象URLと、それぞれに複数のLINE通知先を設定できるようにしなければならない。

#### Scenario: Add multiple monitoring targets
- **WHEN** ユーザーが複数のURLと各監視対象の通知先を設定したとき
- **THEN** システムはすべての監視対象を保存し、次回実行で個別にチェックする

### Requirement: Flexible rule configuration
システムは、各監視対象について通常文字列一致または正規表現による判定をサポートし、出現または消失のどちらを判定対象とするかを設定できるようにしなければならない。

#### Scenario: Configure regex-based detection
- **WHEN** ユーザーが正規表現パターンを設定し、出現/消失の判定を選択したとき
- **THEN** システムはそのルールに従ってページ内容を評価する

### Requirement: Detect changes on appearance or disappearance
システムは、設定されたパターンがページに出現したときと消失したときの両方を検出できなければならない。

#### Scenario: Detect pattern disappearance
- **WHEN** 以前はページにマッチしていたパターンが次回実行でマッチしなくなったとき
- **THEN** システムはその監視対象を変更とみなし、通知を生成する

#### Scenario: Detect pattern appearance
- **WHEN** 以前はページにマッチしていなかったパターンが次回実行でマッチするようになったとき
- **THEN** システムはその監視対象を変更とみなし、通知を生成する

### Requirement: Avoid noisy HTML-only changes
システムは、HTMLの細部差分ではなく、設定されたパターンの出現/消失のみを監視条件として扱わなければならない。

#### Scenario: Unrelated HTML changes do not trigger notification
- **WHEN** ページのHTMLが変わっても、監視対象パターンの出現状態が変わらないとき
- **THEN** システムは通知を生成しない

### Requirement: Maintain previous state across runs
システムは、監視実行の間で前回の判定結果をJSONファイルに保存し、次回実行時に比較できるようにしなければならない。

#### Scenario: Persisted state used for comparison
- **WHEN** GitHub Actionsが再実行されるとき
- **THEN** システムは前回の判定結果を読み込み、新しい取得結果と比較する
