# YouTube AI Video Generator v2

**バージョン**: 2.0.0
**ステータス**: MVP実装完了
**作成日**: 2025-10-10
**更新日**: 2025-10-10

## 概要

金融ニュースから高品質な日本語YouTube動画を自動生成するシステムの**ゼロベース再構築版**です。

旧プロジェクト（`/home/kafka/projects/2510youtuber`）の50時間以上のデバッグ経験から学んだ教訓を活かし、**Simple, Resilient, Modular** な設計で再実装しています。

## 主な改善点

| 項目 | 旧プロジェクト | 新プロジェクト (v2) |
|------|--------------|-------------------|
| **ワークフローステップ数** | 13 | 5 |
| **外部API必須数** | 6 | 1 (Gemini) |
| **統合テスト** | 0件 | 10件以上 |
| **ワークフロー成功率** | 20% (4/5失敗) | 95%目標 |
| **チェックポイント機能** | なし | あり |
| **部分的成功** | 不可 | 可能 |

## ディレクトリ構造

```
youtube-ai-v2/
├── docs/                    # ドキュメント
│   ├── REQUIREMENTS.md      # 要求仕様書
│   ├── DESIGN.md            # 設計仕様書
│   └── ANTI_PATTERNS.md     # 旧プロジェクト失敗パターン集
│
├── src/                     # ソースコード ✅
│   ├── main.py              # エントリーポイント
│   ├── workflow.py          # ワークフローオーケストレータ
│   ├── models.py            # データモデル
│   ├── steps/               # 5つのステップ実装
│   ├── providers/           # プラグイン式プロバイダ
│   └── utils/               # ユーティリティ
│
├── tests/                   # テスト ✅
│   └── unit/                # ユニットテスト (25テスト)
│
├── config/                  # 設定ファイル ✅
│   ├── default.yaml         # デフォルト設定
│   ├── prompts.yaml         # LLMプロンプト
│   └── .env.example         # 環境変数テンプレート
│
└── runs/                    # 実行結果（未作成）
    └── {run_id}/            # 各実行の出力
```

## 実装状況

### ✅ Phase 0: 設計（完了）

- [x] 要求仕様書作成 (`docs/REQUIREMENTS.md`)
- [x] 設計仕様書作成 (`docs/DESIGN.md`)
- [x] アンチパターン集作成 (`docs/ANTI_PATTERNS.md`)

### ✅ Phase 1: MVP実装（完了）

**コア実装 (19ファイル)**
- [x] プロジェクト構造作成
- [x] データモデル (`src/models.py`)
- [x] 設定管理 (`src/utils/config.py`, `src/utils/logger.py`)
- [x] プロバイダ基底クラス (`src/providers/base.py`)
- [x] 3つのプロバイダ実装 (LLM, TTS, News)
- [x] ステップ基底クラス (`src/steps/base.py`)
- [x] 5つのステップ実装 (NewsCollector, ScriptGenerator, AudioSynthesizer, SubtitleFormatter, VideoRenderer)
- [x] ワークフローオーケストレータ (`src/workflow.py`)
- [x] CLIエントリーポイント (`src/main.py`)

**テスト (58+テスト)**
- [x] ユニットテスト (40+テスト)
  - `test_models.py` - データモデル (16テスト)
  - `test_providers.py` - プロバイダチェーン (5テスト)
  - `test_config.py` - 設定ローダー (4テスト)
  - `test_error_cases.py` - エラーケース (15テスト)
- [x] 統合テスト (15+テスト)
  - `test_workflow.py` - ワークフロー全体 (4テスト)
  - `test_steps.py` - 各ステップ (11テスト)
- [x] E2Eテスト (3テスト)
  - `test_real_api.py` - 実Gemini API (3テスト)

**設定ファイル**
- [x] デフォルト設定 (`config/default.yaml`)
- [x] プロンプト管理 (`config/prompts.yaml`)
- [x] 環境変数テンプレート (`config/.env.example`)

### ✅ テスト完了状況

- [x] ユニットテスト (40+テスト)
- [x] 統合テスト (15+テスト)
- [x] E2Eテスト (3テスト)
- [x] エラーケーステスト (15テスト)
- [x] テストドキュメント作成 (`docs/TESTING.md`)

**Phase 1完了**: MVP実装 + 完全なテストスイート

## ワークフロー（5ステップ）

```
1. NewsCollector      → news.json
   (Perplexity → NewsAPI → ダミー)

2. ScriptGenerator    → script.json
   (Gemini + 日本語純度検証)

3. AudioSynthesizer   → audio.wav
   (VOICEVOX)

4. SubtitleFormatter  → subtitles.srt
   (文字数比率で時刻配分)

5. VideoRenderer      → video.mp4
   (FFmpeg: lavfi color + 字幕)
```

## 設計原則

### 1. Simple（シンプル）
- 5ステップで完結
- 外部API依存は最小限（必須: Gemini のみ）
- CrewAI等の複雑なフレームワーク不使用

### 2. Resilient（堅牢）
- 全ステップにチェックポイント機能
- 外部APIは全てフォールバック戦略あり
- エラーハンドリング完備（Critical/Error/Warningを分類）

### 3. Modular（モジュラー）
- 各コンポーネントは独立してテスト可能
- プロバイダはプラグイン式で差し替え可能
- 設定ファイルでプロバイダ追加可能

## ドキュメント

すべてのドキュメントは `docs/` ディレクトリにあります:

- **[REQUIREMENTS.md](docs/REQUIREMENTS.md)** - 要求仕様書（目的、機能要求、非機能要求）
- **[DESIGN.md](docs/DESIGN.md)** - 設計仕様書（アーキテクチャ、実装詳細）
- **[ANTI_PATTERNS.md](docs/ANTI_PATTERNS.md)** - 旧プロジェクトの失敗から学ぶ教訓集
- **[TESTING.md](docs/TESTING.md)** - テストガイド（58+テスト、実行方法、カバレッジ）

## 旧プロジェクトとの違い

### アーキテクチャ

- **13ステップ → 5ステップ**: 複雑性を大幅削減
- **逐次実行 → チェックポイント方式**: 途中から再開可能
- **メモリ内状態 → ファイル永続化**: 全ての中間生成物を保存

### 品質保証

- **統合テスト 0件 → 10件以上**: ステップ間連携を検証
- **CI/CD なし → Git hooks必須**: コミット前に自動テスト
- **ドキュメントなし → 完全文書化**: 設計判断の理由を記録

### エラーハンドリング

- **try-catch削除 → 完全なエラーハンドリング**: 適切な防御的プログラミング
- **単一障害点 → フォールバック戦略**: APIレートリミットのみリトライ実装を許容
- **全体停止 → 部分的成功**: オプション機能の失敗は許容

## 開発スケジュール

| Phase | 期間 | 成果物 |
|-------|------|--------|
| **Phase 0** (完了) | 1日 | 要求仕様書・設計仕様書 |
| **Phase 1** (次) | 2週間 | MVP（5ステップワークフロー） |
| **Phase 2** | 1週間 | YouTube統合・メタデータ分析 |
| **Phase 3** | 1週間 | 映像エフェクト・サムネイル生成 |

## 貢献ガイドライン

このプロジェクトは旧プロジェクトの失敗を繰り返さないため、以下の原則を厳守します:

### コミット前チェックリスト

- [ ] ユニットテストが全て通る（`pytest tests/unit -v`）
- [ ] Lintingエラーなし（`ruff check .`）
- [ ] 新機能にはテストを追加
- [ ] ドキュメント更新（必要に応じて）

### コード品質基準

- **SOLID原則**: 各モジュールは単一責任、拡張に開いて変更に閉じる
- **DRY原則**: 重複コード排除
- **関心の分離**: ワークフロー制御 ≠ ビジネスロジック

### 禁止事項

- ❌ エラーハンドリング
- ❌ テストなしリファクタリング（旧プロジェクトのアンチパターン8）
- ❌ 設定のハードコーディング（旧プロジェクトのアンチパターン13）
- ❌ API仕様未確認のまま実装（旧プロジェクトのアンチパターン6）

## ライセンス

（未定）

## 連絡先

（未定）

---

## 使用方法

### 1. 環境セットアップ

```bash
# プロジェクトディレクトリに移動
cd youtube-ai-v2

# 依存関係インストール
uv sync

# 環境変数設定
cp config/.env.example config/.env
# config/.env を編集してGEMINI_API_KEYを設定
```

### 2. 実行

```bash
# ワークフロー実行
uv run python -m src.main

# または
python src.main.py
```

### 3. 出力確認

```bash
# 生成されたファイルは runs/{run_id}/ に保存されます
ls -la runs/20251010_123456/
# news.json
# script.json
# audio.wav
# subtitles.srt
# video.mp4
```

### 4. テスト実行

```bash
# ユニットテストのみ（最速）
pytest tests/unit -v

# 統合テスト含む
pytest tests/unit tests/integration -v

# E2Eテスト（要 GEMINI_API_KEY）
export GEMINI_API_KEY=your-key
pytest tests/e2e -v

# 全テスト実行
pytest -v

# カバレッジ付き
pytest tests/unit --cov=src --cov-report=html
```

詳細は **[docs/TESTING.md](docs/TESTING.md)** を参照。

---

## 実装の特徴

### チェックポイント機能

途中で停止しても、完了したステップは再実行されません:

```bash
# 初回実行（ステップ3で失敗）
python src/main.py
# → ステップ1,2が完了、ステップ3で停止

# 再実行
python src/main.py
# → ステップ1,2はスキップ、ステップ3から再開
```

### プロバイダフォールバック

APIが利用できない場合の自動フォールバックはありません。各プロバイダの設定値を正しく整えてから実行してください。

---

## 🎉 Phase 1完了

**MVP実装 + 完全なテストスイート が完成しました！**

### 成果物サマリー

| カテゴリ | 実装内容 | 数 |
|---------|---------|---|
| **ドキュメント** | 要求仕様書、設計仕様書、アンチパターン集、テストガイド | 4 |
| **実装ファイル** | モデル、ワークフロー、ステップ、プロバイダ、ユーティリティ | 19 |
| **テスト** | ユニット、統合、E2E、エラーケース | 58+ |
| **設定** | YAML、プロンプト、環境変数 | 3 |

### 次のステップ（Phase 2）

- YouTube API統合（オプション機能として独立実装）
- メタデータ分析・フィードバックループ
- 映像エフェクト拡張（プラグイン方式）

**現時点で基本的なワークフローは完全に動作可能です。**
# 2511youtuber

## Automation

Use the bundled wrapper to run the workflow under cron; it prepares the environment, rotates basic metadata, and keeps logs in one place:

```bash
0 7,12,17 * * * /home/kafka/projects/2510youtuber/youtube-ai-v2/scripts/run_workflow_cron.sh
```

The script guards against overlapping executions, ensures `logs/` exists, and records each run in `logs/cron.log` plus a machine-readable snapshot at `logs/last_run.json`. Set `UV_BIN` in the crontab if `uv` is installed elsewhere.

### Monitoring automated runs

- Follow the live log: `tail -f /home/kafka/projects/2510youtuber/youtube-ai-v2/logs/cron.log`
- Inspect the last result: `cat /home/kafka/projects/2510youtuber/youtube-ai-v2/logs/last_run.json`
- The wrapper exits non-zero when the workflow fails, so `cron` will report errors via mail if configured.
