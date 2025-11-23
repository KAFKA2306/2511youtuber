## 概要
- Cloudflare Workers AI (モデル: @cf/black-forest-labs/flux-1-schnell) ではインフォグラフィック系の文字入りサムネイルが生成不可。文字要素が欠落し、写真主体のみ出力。

## 再現手順
- 環境変数 `CLOUDFLARE_ACCOUNT_ID=dc1aa018702e10045b00865b63f144d0` と有効な API トークンを設定。
- `task thumbnail-test -- 20251123_170000` を実行。
- 出力ファイル: `runs/20251123_170000/thumbnail_ai.png`（内容は画像のみ、テキストなし）。

## 期待と実際
- 期待: 見出しテキストを含むインフォグラフィック調のサムネイル。
- 実際: 背景画像のみで文字要素が生成されない。

## 環境
- モデル: `@cf/black-forest-labs/flux-1-schnell`
- config: `config/default.yaml` の `cloudflare_ai.model` を当該モデルに設定済み。
- 実行日: 2025-11-23

## 打開策
- 文字組み込みが必要な場合は Gemini 3 Image への切替が必要。
- もしくは現行ワークフロー通り、背景生成後に後段でテキストを合成する方式を継続。
