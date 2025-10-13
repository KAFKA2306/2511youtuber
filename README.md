# YouTube AI Video Generator v2

## はじめに
YouTube AI Video Generator v2 は、最新の金融ニュースから日本語の投資解説動画を自動生成するワークフロー型システムです。旧バージョンの複雑さと不安定さを解消し、**シンプル・堅牢・モジュール構成**を徹底して再実装しました。はじめて本プロジェクトを読む方でも全体像がつかめるよう、主要情報を本ドキュメントに集約しています。

## 1. 全体像とゴール
- 目的: 金融ニュースの要約、スクリプト生成、音声合成、字幕整形、動画出力を自動化
- 成果物: `video.mp4`、`audio.wav`、`subtitles.srt`、`script.json`、`news.json`
- 対象視聴者: 明るく専門性のあるキャラクター「春日部つむぎ」が解説する投資チャンネル視聴者
- 運用方針: Gemini を必須 API とし、各ステップにフォールバックとチェックポイントを実装して 95% の成功率を目指す

## 2. 動作環境とセットアップ手順
1. 前提ソフトウェアを用意
   - Python 3.11（`python --version` で確認）
   - [uv](https://github.com/astral-sh/uv) 0.4 以上（`uv --version`）
   - FFmpeg 4.4 以上（`ffmpeg -version`）。Mac の場合は `brew install ffmpeg`、Ubuntu の場合は `apt install ffmpeg` で導入可能
2. 依存関係をインストール
   ```bash
   uv sync
   ```
3. 環境変数を設定
   - `config/.env.example` を `.env` にコピー
   - 必須: `GEMINI_API_KEY`
   - 任意（推奨）: `VOICEVOX_HOST`, `NEWS_API_KEY`, `DISCORD_BOT_TOKEN`
4. ワークフローを実行
   ```bash
   uv run python -m src.main --config config/default.yaml
   ```
5. 生成物とログの確認
   - `runs/{run_id}/` に以下の構造で保存され、再実行時は既存ファイルを自動検出します
     ```
     runs/2025-01-31-120000/
     ├─ inputs/news.json        # 収集したニュース
     ├─ outputs/script.json     # Gemini スクリプト
     ├─ outputs/audio.wav       # 合成音声
     ├─ outputs/subtitles.srt   # 字幕
     ├─ outputs/video.mp4       # 最終動画
     └─ logs/workflow.log       # JSON 形式の構造化ログ
     ```

## 3. ディレクトリと主なモジュール
```
src/
├─ main.py            # CLI エントリーポイント
├─ workflow.py        # 5 ステップを束ねるオーケストレータ
├─ models.py          # データモデルとチェックポイント状態
├─ steps/             # NewsCollector など各ステップの実装
├─ providers/         # LLM / TTS / News のプラグイン実装
└─ utils/             # 設定、ロギング、ファイル操作
config/
├─ default.yaml       # ワークフロー設定
├─ prompts.yaml       # LLM プロンプト
└─ .env.example       # 必須環境変数のテンプレート
tests/                # pytest ベースのユニット・統合・E2E テスト
scripts/              # Discord ボットなど補助スクリプト
assets/               # 動画生成に必要な静的リソース
```

## 4. ワークフローステップ
| # | ステップ名 | 主入力 | 主出力 | フォールバック | チェックポイント |
|---|------------|--------|--------|----------------|------------------|
| 1 | **NewsCollector** | `config/default.yaml` の `news.providers` | `runs/.../inputs/news.json` | オンライン API が失敗した場合はローカルキャッシュ (`assets/news_samples/`) を使用 | 取得済み記事は JSON に保存し再利用 |
| 2 | **ScriptGenerator** | ニュース JSON、`config/prompts.yaml` | `runs/.../outputs/script.json` | Gemini キー枯渇時は予備キー、すべて失敗時は直近成功スクリプトを再提示 | スクリプトを段落単位で保存 |
| 3 | **AudioSynthesizer** | スクリプト JSON、`config/default.yaml.tts` | `runs/.../outputs/audio.wav` | VOICEVOX 不達時は pyttsx3 に切替 | 話者ごとの WAV を結合し中間ファイルを保持 |
| 4 | **SubtitleFormatter** | スクリプト JSON、音声長 | `runs/.../outputs/subtitles.srt` | 文字数超過時は自動で文分割 | フォーマット済み字幕を保存 |
| 5 | **VideoRenderer** | 背景素材 (`assets/background.mp4`)、音声、字幕 | `runs/.../outputs/video.mp4` | 背景動画欠損時は単色背景を生成 | FFmpeg コマンドと実行ログを記録 |

各ステップは開始・終了イベントを構造化ログに記録し、成功時に成果物をファイルへ保存してから次へ進みます。途中で失敗した場合も既存成果物は保持され、再実行時には出力ファイルの存在チェックによって自動スキップされます。

## 5. 品質保証
| 項目 | コマンド | 実施タイミング | 目的 |
|------|----------|----------------|------|
| ユニットテスト | `uv run pytest tests/unit -v --maxfail=1` | すべてのコミット前 | モデル・ユーティリティの単体検証 |
| 統合テスト | `uv run pytest tests/integration -v` | PR 作成前 | ステップ間連携とフォールバック挙動の確認 |
| E2E テスト | `uv run pytest -v -m e2e --runslow` | リリース前・週次 | 実 API を使用し主要シナリオ 3 件を検証 |
| カバレッジ | `uv run pytest tests/unit -m unit -v --cov=src --cov-report=term-missing` | 週次レポート | 80% 以上のカバレッジ維持 |
| 静的検査 | `uv run ruff check src tests` | PR 作成前 | コード規約とバグ起因パターンの検出 |
| 整形 | `uv run ruff format src tests` | 必要時 | フォーマット統一 |

失敗したテストは `runs/{run_id}/logs/workflow.log` の出力例と照らし合わせて原因を特定し、再現手順を README に追記してから修正する運用です。

## 6. 設計のキーポイント
- **Simple**: ステップを 5 つに厳選し、Gemini を唯一の必須外部 API とすることで制御フローを単純化
- **Resilient**: 各ステップ完了時に `WorkflowState` へ状態を永続化し、失敗時も途中成果物を保持
- **Observable**: すべての重要イベントを JSON ログに記録し、Grafana／Loki で可視化できる形式を維持
- **Modular**: `src/providers/` に TTS・LLM・ニュースのプラグインを分離し、設定値のみで差し替え可能
- **WorkflowState**: `src/models.py` の `WorkflowState` が run_id、完了ステップ、出力パス、エラーを追跡し、`runs/<run_id>/state.json` を参照しながら同じ run_id で再生成されたオーケストレータから中断地点を自動復元

### 設定ファイルの読み解き方
- `config/default.yaml`
  - `news.providers`: 優先順位付きのニュース API リスト（`type`, `api_key_env`, `cache_path`）
  - `script`: Gemini プロンプトテンプレートと温度設定
  - `tts`: 利用する音声エンジンと話者マッピング
  - `video`: FFmpeg プリセット、出力解像度、字幕スタイル
- `config/prompts.yaml`
  - キャラクター「春日部つむぎ」の語彙リスト
  - 真面目モード／ギャルモードの切替条件
  - ニュース要約時の必須指標 (株価、金利、為替)

## 7. 要件の抜粋と失敗から得た知見
- **機能要件 (Phase 1)**: ニュース 3 件 → 対話形式スクリプト → 話者別 TTS → 字幕付き 1080p 動画をローカル保存
- **非機能要件**: 95% 以上のワークフロー成功率、テストカバレッジ 80% 以上、音声同期 ±100ms 以内
- **品質指標**
  - スクリプト: 5〜10 分尺、話者交代 10 回以上、WOW スコア 6.0 以上
  - 音声: 24kHz WAV、話者識別可能
  - 動画: 1920x1080 / 25fps、字幕コントラスト比 4.5:1 以上
- **再発防止メモ**
  - 旧版は 13 ステップ直列・ 8 API 依存で 66% 稼働率 → 必須機能だけを 5 ステップに圧縮
  - 状態をメモリ管理していたためクラッシュで成果物消失 → すべてファイルへ永続化
  - テストゼロでフォーマット崩れを見逃した → ユニット / 統合 / E2E をコミットフローに組み込み

## 8. キャラクターとコンテンツ方針
- **主役**: VOICEVOX 春日部つむぎ（ギャル語と専門トーンを切替）
- **構成テンプレ**
  1. 「放課後速報」で市場指標を 30 秒で提示
  2. 視聴者質問を引用し、長期視点の解説を 3 分で展開
  3. 次回予告とコメント募集
- **補助キャラクター**: ずんだもん（要点リキャップ）、玄野武宏（リスク警告）
- **スクリプト反映ポイント**: `config/prompts.yaml.script_style.lexicon` にギャル語辞書、`...serious_mode` に真面目トーン指示を記述
- **コンプライアンス**: 金融商品勧誘を避けるため「投資判断は自己責任」と締める行を必ず挿入

## 9. 運用ノート（Discord ニュースボット）
- 目的: Discord サーバーに最新ニュースを配信し、動画生成の素材にする
- 起動スクリプト: `./scripts/run_discord_news_bot.sh`
- 必要変数: `.env` に `DISCORD_BOT_TOKEN`, `NEWS_API_KEY`
- 実行前テスト: `uv run python scripts/discord_news_bot.py --dry-run` で投稿内容を標準出力に確認
- 常駐化: systemd で稼働させる場合は以下の設定例を使用
  ```ini
  [Unit]
  Description=Discord News Bot
  After=network-online.target

  [Service]
  Type=simple
  WorkingDirectory=/workspace/2511youtuber
  ExecStart=/workspace/2511youtuber/scripts/run_discord_news_bot.sh
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

## 10. 今後の拡張のヒント
- LLM や TTS のプロバイダは `config/default.yaml` で切替可能。新プロバイダを追加する際はテストとフォールバックを先に用意
- `runs/{run_id}/` をバージョン管理対象外にすることで、出力物を安全に保管
- 新シナリオを追加する場合は、スクリプトテンプレートとテストケースを同時に更新して品質基準を維持

---
### トラブルシューティングのチェックリスト
- **Gemini から 429 が返る**: `.env` に予備 API キーを追加し、`config/default.yaml.script.api_keys` に列挙
- **VOICEVOX 接続不可**: `VOICEVOX_HOST=http://localhost:50021` を設定し、`scripts/voicevox_manager.sh start` を使用
- **FFmpeg エラー (filter not found)**: `ffmpeg -version` で 4.4 以上を確認し、古いバージョンの場合はアップグレード
- **字幕ズレ**: `runs/.../outputs/audio_segments/` を確認し、セグメント長が極端に短い場合は `config/default.yaml.subtitle.max_chars` を減らす

---
この README だけでプロジェクトの背景・使い方・設計意図まで把握できる構成にしています。詳細を深掘りしたい場合は、ソースコードと設定ファイルをあわせて参照してください。
