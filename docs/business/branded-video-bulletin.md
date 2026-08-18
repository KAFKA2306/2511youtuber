# 金融メディア向け動画制作

このリポジトリの既存フローを使い、金融・経済メディア向けにブランド名と開示文を付けた動画サンプルを生成できます。顧客向けrunは既存のdry-run経路を強制し、YouTubeへ外部送信しません。

現在実装されているブランド設定は次の3項目です。

- `brand_id` — 設定を識別する小文字のID
- `display_name` — YouTube用タイトルへ付ける表示名
- `disclosure_text` — YouTube用説明文へ追加する開示文

サンプル設定は [`config/brands/example.yaml`](../../config/brands/example.yaml) です。

```bash
task run -- --brand-config config/brands/example.yaml --news-query "半導体 AI 決算"
```

`--brand-config`を指定すると、通常設定がpublic公開でも、このrunでは既存の`--dry-run`と同じ非公開検証経路を使用します。`runs/<run_id>/youtube.json`には、外部副作用がないこと、ブランドID・表示名・ブランド設定のSHA-256、ニュース取得結果にURLがある場合はそのURLと公表日時を保存します。`review.approved`は`false`で生成されます。

YouTube Data APIの動画リソースで指定できる`status.privacyStatus`は`private`、`public`、`unlisted`です。API仕様は [Google for Developers — Videos](https://developers.google.com/youtube/v3/docs/videos) を参照してください。

## 提供できる範囲

現時点では、既存のニュース取得、台本、VOICEVOX音声、字幕、動画レンダリング、YouTube用メタデータ生成を再利用し、公開前に確認できるブランド付きサンプルを作るところまでを対象にします。顧客ロゴ、顧客別intro/outro、顧客YouTubeチャンネルへの承認付き公開、継続案件管理はまだ実装していません。

顧客名、受注件数、売上、成果指標は実績が確認できるまで掲載しません。

## 相談

公開Issueには秘密情報、未公開記事本文、APIキー、顧客の個人情報を書かないでください。

- [1本デモを相談する](https://github.com/KAFKA2306/2511youtuber/issues/new?title=1%E6%9C%AC%E3%83%87%E3%83%A2%E3%82%92%E7%9B%B8%E8%AB%87)
- [4週間PoCを相談する](https://github.com/KAFKA2306/2511youtuber/issues/new?title=4%E9%80%B1%E9%96%93PoC%E3%82%92%E7%9B%B8%E8%AB%87)

相談時は、公開可能な範囲で媒体の種類、動画化したいテーマ、希望頻度、希望時期を記載してください。
