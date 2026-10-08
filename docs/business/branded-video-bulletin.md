# 金融メディア向け Branded Video Bulletin

このリポジトリの既存フローを使い、金融・経済メディア向けのブランド付き動画を生成します。ブランド案件は、明示承認が無い限り既存の dry-run 経路に固定され、YouTube へ外部送信しません。

## ブランド設定

`config/brands/example.yaml` と同じ versioned YAML を使います。

- `schema_version`
- `brand_id`
- `display_name`
- `disclosure_text`
- `allowed_topics`
- `default_visibility`
- `intro` / `outro`

intro/outro を使う場合は、repository-relative path と `rights_confirmed: true` を同時に指定します。権利確認が false の素材、絶対パス、`..` を含む参照は fail closed で拒否します。

```yaml
schema_version: 1
brand_id: example-financial-media
display_name: Example Financial Media
disclosure_text: 公開前レビュー用のサンプルです。
allowed_topics: [半導体, AI]
default_visibility: private
intro:
  path: assets/brand/intro.mp4
  rights_confirmed: true
outro: null
```

`allowed_topics` が設定されている場合、ブランドrunは `--news-query` を必須にし、許可トピックを1つも含まない query を拒否します。

## 1. レビュー用 run

```bash
task run -- --brand-config config/brands/example.yaml --news-query "半導体 AI 決算"
```

承認ファイルが無いブランドrunは必ず dry-run/private です。既存の `youtube.json` に `review` を追加し、次を追跡します。

- review status: `pending`
- brand schema version / brand ID / config SHA-256
- source URL / source date
- script / rendered video / metadata の path、SHA-256、size
- intended visibility
- external side effect が無いこと

## 2. 明示承認後の既存公開経路

公開を許可する場合だけ、ローカルの承認ファイルを作ります。承認は brand ID と brand config の exact SHA-256 に紐づきます。別設定への流用は拒否します。

```json
{
  "schema_version": 1,
  "brand_id": "example-financial-media",
  "brand_config_sha256": "<exact 64-char sha256>",
  "approved": true,
  "approved_by": "<reviewer>",
  "approved_at": "2026-10-08T20:00:00+09:00"
}
```

```bash
task run -- \
  --brand-config config/brands/example.yaml \
  --brand-approval /secure/local/example.approval.json \
  --news-query "半導体 AI 決算"
```

承認済みrunだけが既存 `YouTubeClient` の公開工程へ進みます。別 uploader は作りません。公開範囲は brand config の `default_visibility` を使います。sample は `private` です。

承認ファイルには credential を入れず、repository へ commit しないでください。

## 提供範囲と責任境界

既存のニュース取得、台本、VOICEVOX音声、字幕、動画レンダリング、metadata、YouTube uploader を再利用します。ブランド固有 intro/outro は権利確認済み参照だけを受け付けます。顧客名、契約、売上、継続利用などは実データで観測できた場合だけ記録し、未観測は `UNVERIFIED` のまま扱います。

CTA/event contract は `config/business_events.yaml` を正本とし、synthetic/test と actual observation を分離します。synthetic を売上や顧客成果として数えません。

## 相談

既存の動画制作機能を使い、まず1本のレビュー用サンプルを検討できます。4週間PoCの本数・費用・公開可否は相談後に個別に決定します。Issue作成だけでは発注・契約・公開にはなりません。


公開Issueには秘密情報、未公開記事本文、APIキー、顧客の個人情報を書かないでください。

- [1本デモを相談する](https://github.com/KAFKA2306/2511youtuber/issues/new?title=Branded%20Video%20Bulletin%EF%BD%9C1%E6%9C%AC%E3%83%87%E3%83%A2%E7%9B%B8%E8%AB%87&body=%E5%85%AC%E9%96%8BIssue%E3%81%A7%E3%81%99%E3%80%82%E6%A9%9F%E5%AF%86%E6%83%85%E5%A0%B1%E3%83%BB%E5%80%8B%E4%BA%BA%E6%83%85%E5%A0%B1%E3%83%BB%E6%9C%AA%E5%85%AC%E9%96%8B%E5%8E%9F%E7%A8%BF%E3%83%BB%E5%A5%91%E7%B4%84%E6%9D%A1%E4%BB%B6%E3%81%AF%E6%9B%B8%E3%81%8B%E3%81%AA%E3%81%84%E3%81%A7%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84%E3%80%82%0A%0A-%20%E5%AA%92%E4%BD%93%E3%81%AE%E7%A8%AE%E9%A1%9E%EF%BC%88%E5%85%AC%E9%96%8B%E3%81%A7%E3%81%8D%E3%82%8B%E7%AF%84%E5%9B%B2%EF%BC%89%3A%20%0A-%20%E5%8B%95%E7%94%BB%E5%8C%96%E3%81%97%E3%81%9F%E3%81%84%E3%83%86%E3%83%BC%E3%83%9E%3A%20%0A-%20%E5%B8%8C%E6%9C%9B%E3%81%99%E3%82%8B%E5%8B%95%E7%94%BB%E3%81%AE%E9%95%B7%E3%81%95%3A%20%0A-%20%E5%B8%8C%E6%9C%9B%E6%99%82%E6%9C%9F%3A%20)
- [4週間PoCを相談する](https://github.com/KAFKA2306/2511youtuber/issues/new?title=Branded%20Video%20Bulletin%EF%BD%9C4%E9%80%B1%E9%96%93PoC%E7%9B%B8%E8%AB%87&body=%E5%85%AC%E9%96%8BIssue%E3%81%A7%E3%81%99%E3%80%82%E6%A9%9F%E5%AF%86%E6%83%85%E5%A0%B1%E3%83%BB%E5%80%8B%E4%BA%BA%E6%83%85%E5%A0%B1%E3%83%BB%E6%9C%AA%E5%85%AC%E9%96%8B%E5%8E%9F%E7%A8%BF%E3%83%BB%E5%A5%91%E7%B4%84%E6%9D%A1%E4%BB%B6%E3%81%AF%E6%9B%B8%E3%81%8B%E3%81%AA%E3%81%84%E3%81%A7%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84%E3%80%82%0A%0A-%20%E5%AA%92%E4%BD%93%E3%81%AE%E7%A8%AE%E9%A1%9E%EF%BC%88%E5%85%AC%E9%96%8B%E3%81%A7%E3%81%8D%E3%82%8B%E7%AF%84%E5%9B%B2%EF%BC%89%3A%20%0A-%20%E5%8B%95%E7%94%BB%E5%8C%96%E3%81%97%E3%81%9F%E3%81%84%E3%83%86%E3%83%BC%E3%83%9E%3A%20%0A-%20%E9%80%B1%E3%81%82%E3%81%9F%E3%82%8A%E3%81%AE%E6%83%B3%E5%AE%9A%E6%9C%AC%E6%95%B0%3A%20%0A-%20%E5%B8%8C%E6%9C%9B%E9%96%8B%E5%A7%8B%E6%99%82%E6%9C%9F%3A%20)

相談時は、公開可能な範囲で媒体の種類、動画化したいテーマ、希望頻度、希望時期を記載してください。
