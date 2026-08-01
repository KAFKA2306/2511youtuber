# YouTube AI Video Generator v2

**リポジトリ:** https://github.com/KAFKA2306/2511youtuber

日々のニュースから、日本語の金融・経済動画を生成するワークフローです。ニュース取得、台本生成、シーン画像生成、VOICEVOX音声、字幕、FFmpeg動画、サムネイル、メタデータを独立した工程として接続します。

旧版の[2510youtuber](https://github.com/KAFKA2306/2510youtuber)を整理し、設定、チェックポイント、サービス管理、テスト、定期実行を強化した後継プロジェクトです。

## 処理の流れ

```text
ニュース候補を取得
  → 出典・日時・重複を確認
  → Gemini系プロバイダーで日本語台本を生成
  → シーン画像を生成
  → VOICEVOXで音声を生成
  → 字幕時間を割り当て
  → FFmpegで動画をレンダリング
  → サムネイル・説明文などを生成
  → 人間が内容と権利を確認
  → 設定で有効な場合だけ配信処理へ進む
```

## 主な工程

| 工程 | 実装 | 主な出力 |
| --- | --- | --- |
| ニュース取得 | `src/steps/news.py` | `news.json` |
| 台本生成 | `src/steps/script.py` | `script.json` |
| シーン生成 | `src/steps/scene_generator.py` | `scene_manifest.json` |
| 音声合成 | `src/steps/audio.py` | `audio.wav` |
| 字幕生成 | `src/steps/subtitle.py` | `subtitles.srt` |
| 動画生成 | `src/steps/video.py` | `video.mp4` |

メタデータ、サムネイル、アップロード、SNS配信は`config/default.yaml`で有効化された場合のみ実行します。

## 必要環境

- Pythonと`uv`
- `go-task`
- FFmpeg
- VOICEVOX Engine
- 利用するニュース・LLMプロバイダーの認証情報
- シーン画像生成を使う場合はPyTorch対応環境と十分なVRAM

`apt install taskwarrior`は`go-task`とは別製品なので使用しません。Taskの導入は公式のgo-task手順を使用してください。

## 初期設定

```bash
task bootstrap
```

このタスクは、リポジトリの現在のTask定義に従い、依存関係、補助サービス、定期実行設定を構成します。実行前に内容を確認してください。特にcron登録や常駐サービスの変更は、利用環境へ影響します。

手動設定:

```bash
uv sync
cp config/.env.example config/.env
```

`config/.env`へ必要なAPIキーを設定します。秘密情報はコミットしません。

## 動画生成

```bash
task run
task youtube:run
task youtube:dev
```

ニュース検索語を指定する例:

```bash
task run -- --news-query "FOMC 金利"
```

シーン生成の個別確認:

```bash
uv run python scripts/test_scene_gen.py <run_id>
```

## サービス管理

```bash
task services:start
task services:status
task voicevox:start
task voicevox:stop
task discord:start
task aim:dashboard
```

常駐サービスを起動する前に、ポート、ログ保存先、既存プロセスとの競合を確認してください。

## シーン画像生成

設定は`config/default.yaml`と`config/scene_prompts.yaml`にあります。

```yaml
steps:
  scene:
    enabled: true
    images_per_video: 4
    variants_per_type: 2
    batch_size: 2
    compile_model: false
    width: 1280
    height: 720
    num_steps: 9
```

`batch_size`を増やすと高速化する可能性がありますが、必要VRAMも増えます。速度倍率はGPU、モデル、解像度、ドライバーに依存するため、READMEでは固定値を保証しません。

画像生成の抽象化は`src/services/image_generation.py`にあり、`SceneGenerator`へ依存注入します。

## 設定ファイル

| ファイル | 内容 |
| --- | --- |
| `config/default.yaml` | 工程の有効化、動画設定、プロバイダー設定 |
| `config/prompts.yaml` | ニュース・台本・メタデータ用プロンプト |
| `config/scene_prompts.yaml` | シーン画像のプロンプト |
| `config/.env` | APIキーなどの非公開設定 |
| `assets/` | フォント、キャラクター画像、動画素材 |

## テスト

```bash
task test:fast
task test:all
task lint
task format
```

- `test:fast` — 動画レンダリングなど重い処理を省いた主要工程の検証
- `test:all` — リポジトリが定義する全テスト

一部のE2Eテストは実API、VOICEVOX、FFmpegを利用します。テスト成功は、その実行環境・入力・時点における確認であり、YouTube公開、本番運用、すべてのニュース内容の正確性を保証しません。

## 自動実行

リポジトリにはcronを構成する仕組みがあります。

```bash
task automation:init
task automation:cron
task automation:setup
```

README作成時の設定例では4時間ごとの実行を想定していますが、実際の登録内容は`scripts/automation.py`と現在のcrontabを確認してください。

ログ例:

```text
logs/automation/workflow_4hourly.log
```

## 主な構成

```text
apps/       CLIなどのアプリケーション入口
config/     YAML設定、プロンプト、環境変数例
docs/       システム・運用文書
scripts/    サービス管理、定期実行、診断
src/        ワークフロー、プロバイダー、各工程
tests/      単体・統合・E2Eテスト
runs/       実行ごとの生成物
```

詳細:

- [システム概要](docs/system_overview.md)
- [運用手順](docs/operations.md)
- [自動実行プレイブック](docs/automation_playbook.md)
- [開発ルール](AGENTS.md)

## 公開前の必須確認

- ニュースの一次情報と発生日
- 数値、企業名、人物名、日付
- 台本が出典の意味を変えていないか
- 画像、音楽、フォント、VOICEVOX話者の利用条件
- 誹謗中傷、個人情報、著作権侵害の有無
- YouTubeタイトル・説明文が誤認を招かないか
- 自動アップロードが意図的に有効化されているか

**README最終監査:** 2026-08-01
