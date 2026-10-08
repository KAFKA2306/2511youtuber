# YouTube performance feedback contract

Issue #51 のパフォーマンスフィードバックは、YouTube Analytics の実測値だけを入力にする。

## Supported metrics

v1 は YouTube Analytics の次の metric を扱う。

- `views`
- `likes`
- `averageViewDuration`
- `estimatedMinutesWatched`

取得元は `youtubeAnalytics.reports.query`。channel owner 向け query は `ids=channel==MINE`、`dimensions=video`、`filters=video==<video_id>` を使用する。credential は runtime から渡し、repository、fixture、log、Issue、PR に保存しない。

Primary specifications:

- https://developers.google.com/youtube/analytics/metrics
- https://developers.google.com/youtube/analytics/reference/reports/query
- https://developers.google.com/youtube/analytics/channel_reports

## Observation ledger

`schema_version` は `youtube-performance.v1`。

各 observation は次へ遡れる。

- video ID / topic
- observation period
- retrieved_at
- 4 metrics
- source provider
- source endpoint
- exact query parameters

API response の `columnHeaders` を名前で解決し、列不足、video不一致、重複video ID、負値、整数でない views/likes は fail closed にする。API failure は fixture や0で置換しない。rows が無い場合は observation を生成しない。

`not_instrumented` は未接続状態であり、0 views ではない。`measured` は API query を実行して保存した ledger を表す。

## Pattern extraction

最低5本の measured observation が揃うまでは `INSUFFICIENT_EVIDENCE`。5本以上でも、`averageViewDuration` が標本中央値以上かつ同一topicが2本以上ある場合だけ `MEASURED` pattern を生成する。それ以外は `NO_SUPPORTED_PATTERN`。

pattern には元 video ID、観測期間、retrieved_at、provider を evidence として保持する。相関を因果として扱わない。

## ScriptGenerator integration

`steps.script.performance_feedback_path` が設定された時だけ ledger を読み込む。未設定が既定値であり、従来の生成挙動は変えない。

設定された場合:

1. ledger を検証する。
2. pattern state と evidence trace を `runs/<run_id>/performance_context.json` に保存する。
3. state が `MEASURED` の時だけ補助contextを script prompt へ追記する。
4. `INSUFFICIENT_EVIDENCE` / `NO_SUPPORTED_PATTERN` では prompt を増やさない。
5. tracker に performance state、sample size、evidence video IDs を残す。

実YouTube Analytics APIをこの環境からまだ観測していない場合、その runtime evidence は `UNVERIFIED` のまま扱う。これはrepository側の adapter、保存、pattern extraction、prompt wiring の完了とは分離する。
