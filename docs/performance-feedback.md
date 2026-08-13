# YouTube performance feedback contract

Issue #51 のパフォーマンスフィードバックは、YouTube Analytics の実測値だけを入力にする。

## Supported metrics

YouTube Analytics API の一次仕様で確認できる次の metric だけを v1 の必須入力とする。

- `views`
- `likes`
- `averageViewDuration`
- `estimatedMinutesWatched`

取得処理は API credential を repository に保存してはならない。API 応答を正規化した各 observation は `video_id`, `period_start`, `period_end`, `retrieved_at`, `topic`, `evidence_url` と上記4 metric を保持する。

Primary specifications:

- https://developers.google.com/youtube/analytics/metrics
- https://developers.google.com/youtube/analytics/reference/reports/query

## Measurement states

`schema_version` は `youtube-performance.v1` とする。

- `not_instrumented`: まだ実 API 計測を接続していない。`0 views` を意味しない。
- `measured`: 実 API 由来の observation が存在する。

未知値を0へ変換しない。

## Pattern extraction

成功パターンは最低5本の measured observation が揃うまで生成しない。v1 は `averageViewDuration` の標本中央値以上の動画から、2本以上で繰り返された `topic` だけを補助コンテキスト候補とする。

これは因果推論ではない。script generation に渡す場合も補助コンテキストと明記し、元 `video_id` を evidence として併記する。十分な母数がない、または繰り返しパターンがない場合は空文字列を返し、promptへ架空の成功則を追加しない。

## Remaining integration work

実 API 取得を行うには OAuth credential を安全な runtime secret として設定し、`reports.query` の実応答をこの contract に正規化する必要がある。実 API 応答が取得できるまでは Issue #51 の「実APIレスポンスで検証」は未完了として扱う。
