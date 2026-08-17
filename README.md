# 2511youtuber — 金融ニュース動画の生成・公開パイプライン

[![Default config safety](https://github.com/KAFKA2306/2511youtuber/actions/workflows/default-config-safety.yml/badge.svg)](https://github.com/KAFKA2306/2511youtuber/actions/workflows/default-config-safety.yml)
[![Storyboard contract](https://github.com/KAFKA2306/2511youtuber/actions/workflows/storyboard-contract.yml/badge.svg)](https://github.com/KAFKA2306/2511youtuber/actions/workflows/storyboard-contract.yml)
[![Provider internet boundary](https://github.com/KAFKA2306/2511youtuber/actions/workflows/provider-internet-boundary.yml/badge.svg)](https://github.com/KAFKA2306/2511youtuber/actions/workflows/provider-internet-boundary.yml)

ニュース取得、台本生成、VOICEVOX音声、字幕、FFmpeg動画、メタデータ生成、YouTube公開までを一つの実行で処理します。

## 現在の既定動作

`task run`または`python -m src.main`を通常実行すると、生成完了後にYouTubeへ**public公開**します。

```yaml
steps:
  metadata:
    enabled: true
  youtube:
    enabled: true
    dry_run: false
    default_visibility: public
```

通常入口では、YouTubeクライアントの外部投稿承認とpublic公開承認もプロセス内で設定します。したがって、別の承認用環境変数を手作業で設定する必要はありません。

ただし、次が不足している場合は公開せず失敗終了します。

- Geminiなど、生成工程に必要なAPI資格情報
- YouTube OAuthのclient ID / client secret
- VOICEVOXおよびFFmpegなどの実行依存
- 有効な動画ファイル
- 空でないタイトルと説明文
- YouTube APIから返されるvideo ID

## セットアップ

```bash
uv sync
cp config/.env.example config/.env
# config/.envへ必要なAPIキーとYouTube OAuth情報を設定

task run
```

初回のYouTube投稿時はブラウザでOAuth認証が開きます。認証トークンはJSON形式で保存され、利用可能な環境では権限を`0600`へ制限します。

## 公開せず検証する

外部公開を止めて生成・投稿準備だけを確認する場合は、明示的に`--dry-run`を指定します。

```bash
task run -- --dry-run
# または
uv run python -m src.main --dry-run
```

この場合はYouTube設定を実行時に次へ上書きします。

```yaml
youtube:
  enabled: true
  dry_run: true
  default_visibility: private
```

## 動画生成の正準境界

生成AI動画を使う場合も、ベンダー固有promptを正準データにはしません。正準線は次です。

```text
News / Evidence
  → Script
  → VideoStoryboard
  → Shot
  → Provider Adapter / deterministic renderer
  → Rendered Artifact
  → Audit
  → Publish
```

`src/storyboard.py` の `VideoStoryboard` / `Shot` が時間軸、構図、動き、文字演出、参照素材、禁止事項を保持します。`src/providers/video_generation.py` の `StoryboardPromptCompiler` が同じStoryboardをprovider向けpromptへ決定論的にcompileし、`MiniMaxH3Provider` はMiniMax H3 V2境界だけを担当します。既存のFFmpeg/Remotionレンダリング経路は削除せず、生成AI providerとは別のrendererとして残します。

MiniMaxを実呼び出しする場合のみ`MINIMAX_API_KEY`が必要です。テストは`compile_request()`までで停止し、外部APIやYouTubeへ送信しません。

## 基本フロー

```text
ニュース候補取得
  → 台本生成
  → 音声・字幕生成
  → 動画レンダリング
  → タイトル・説明・タグ生成
  → YouTube OAuth
  → public公開
```

Twitter、LinkedIn、はてな、Buzzsprout、自動cron運用は既定では無効です。現在「そのまま実行して外部公開する」対象はYouTubeです。

## 実行コマンド

```bash
task run
task run -- --news-query "半導体 AI 決算"
task run -- --dry-run
task check
```

## テスト対象

- 通常実行がYouTube public公開設定であること
- `--dry-run`が外部投稿承認を除去すること
- 空動画・空タイトル・空説明文を拒否すること
- OAuth資格情報不足時に公開成功扱いしないこと
- API応答にvideo IDがない場合に失敗すること
- YAMLに`steps.news`が重複していないこと
- Storyboardのtimeline overlap / gap policy / duration overflowをfail closedすること
- 1 Shot 1 messageの最小lintが動くこと
- 12秒・5 Shot fixtureをprovider requestへ決定論的にcompileできること

## 運用上の注意

- 投稿された内容は即時に外部公開されます
- ニュース本文、画像、立ち絵、音声、BGM、フォントの利用条件を確認してください
- 株価、決算、経済統計には基準日と単位を付けてください
- LLM生成文を一次情報として扱わないでください
- 公開前確認が必要な実行では必ず`--dry-run`を使用してください

**README最終更新:** 2026-08-12
