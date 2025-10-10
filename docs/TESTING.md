# テストガイド - YouTube AI Video Generator v2

**作成日**: 2025-10-10

---

## テスト構成

### テストカテゴリ

| カテゴリ | ファイル数 | テスト数 | 実行時間 | 説明 |
|---------|----------|---------|---------|------|
| **Unit** | 4 | 40+ | <1秒 | 個別関数・クラスのテスト |
| **Integration** | 2 | 15+ | 数秒 | ステップ間連携テスト |
| **E2E** | 1 | 3 | 数分 | 実API使用の完全テスト |

### ディレクトリ構造

```
tests/
├── conftest.py              # 共通フィクスチャ
├── fixtures/                # テストデータ
│   ├── sample_news.json
│   └── sample_script.json
├── unit/                    # ユニットテスト
│   ├── test_models.py       # データモデル (16テスト)
│   ├── test_providers.py    # プロバイダチェーン (5テスト)
│   ├── test_config.py       # 設定ローダー (4テスト)
│   └── test_error_cases.py  # エラーケース (15テスト)
├── integration/             # 統合テスト
│   ├── test_workflow.py     # ワークフロー全体 (4テスト)
│   └── test_steps.py        # 各ステップ (11テスト)
└── e2e/                     # E2Eテスト
    └── test_real_api.py     # 実Gemini API (3テスト)
```

---

## テスト実行方法

### 1. ユニットテストのみ（推奨）

```bash
# 最速・外部依存なし
pytest tests/unit -v

# カバレッジ付き
pytest tests/unit --cov=src --cov-report=html
```

### 2. 統合テスト含む

```bash
# ダミープロバイダ使用
pytest tests/unit tests/integration -v

# または
pytest -m "unit or integration"
```

### 3. E2Eテスト（実API使用）

```bash
# 環境変数設定が必要
export GEMINI_API_KEY=your-key-here
pytest -m e2e -v

# すべて実行
pytest -v
```

### 4. 特定のテストのみ

```bash
# 単一ファイル
pytest tests/unit/test_models.py -v

# 単一テストクラス
pytest tests/unit/test_models.py::TestScriptSegment -v

# 単一テスト関数
pytest tests/unit/test_models.py::TestScriptSegment::test_valid_segment -v
```

---

## ユニットテスト詳細

### test_models.py (16テスト)

**日本語検証**:
- `test_pure_japanese_*` - ひらがな、カタカナ、漢字の検証
- `test_not_pure_japanese_*` - 英単語混入の検出

**ScriptSegment**:
- `test_valid_segment` - 正常なセグメント作成
- `test_reject_english_text` - 英語拒否
- `test_reject_mixed_text` - 混在拒否

**WorkflowState**:
- `test_mark_completed` - ステップ完了マーク
- `test_mark_failed` - 失敗処理
- `test_mark_success` - 成功処理

### test_providers.py (5テスト)

**ProviderChain**:
- `test_first_provider_succeeds` - 優先順位1が成功
- `test_fallback_to_second_provider` - フォールバック動作
- `test_skip_unavailable_provider` - 利用不可プロバイダスキップ
- `test_all_providers_fail` - 全失敗時のエラー
- `test_priority_ordering` - 優先順位ソート

### test_error_cases.py (15テスト)

**スクリプトパースエラー**:
- `test_malformed_yaml` - 不正なYAML
- `test_json_fallback_on_yaml_error` - YAML→JSONフォールバック
- `test_max_recursion_depth` - 再帰深度制限

**日本語純度検証**:
- `test_reject_english_in_script` - 英語拒否
- `test_reject_mixed_language` - 混在拒否
- `test_accept_pure_japanese_with_numbers` - 数字許可

**プロバイダエラー**:
- `test_all_providers_fail` - 全プロバイダ失敗
- `test_unavailable_providers_skipped` - 未利用スキップ

**ステップエラー**:
- `test_missing_input_file` - 入力ファイル不在
- `test_step_without_output_file` - 出力ファイル不在

---

## 統合テスト詳細

### test_workflow.py (4テスト)

**フルワークフロー**:
- `test_full_workflow_with_dummy_providers` - 全ステップ実行
- `test_checkpoint_resume` - チェックポイント再開
- `test_workflow_state_persistence` - 状態永続化
- `test_partial_workflow_failure` - 部分失敗処理

**検証項目**:
- 5ステップすべてが実行される
- `runs/{run_id}/` に全ファイルが保存される
- 再実行時に完了ステップがスキップされる
- エラー時も完了ステップの成果物は保持される

### test_steps.py (11テスト)

**NewsCollector**:
- `test_news_collection_creates_valid_output` - ニュース収集

**ScriptGenerator**:
- `test_script_generation_with_dummy_llm` - ダミーLLMでスクリプト生成
- `test_script_recursive_yaml_parsing` - 再帰的YAMLパース

**AudioSynthesizer**:
- `test_audio_synthesis_with_pyttsx3` - pyttsx3で音声合成

**SubtitleFormatter**:
- `test_subtitle_generation` - SRT形式字幕生成
- `test_timestamp_calculation` - タイムスタンプ計算

---

## E2Eテスト詳細

### test_real_api.py (3テスト)

**前提条件**: `GEMINI_API_KEY` 環境変数が必要

**テスト内容**:
1. `test_gemini_api_availability` - Gemini API接続確認
2. `test_gemini_script_generation` - 実LLMでスクリプト生成
3. `test_full_workflow_with_real_gemini` - ニュース→スクリプト生成まで

**注意**:
- APIコストが発生します（Gemini Flash: 無料枠あり）
- ネットワーク必須
- レート制限により失敗する可能性あり

---

## テストカバレッジ

### 目標

- **ユニットテスト**: 80%以上
- **統合テスト**: 主要パス100%
- **E2E**: 1本以上の完全ワークフロー

### カバレッジ確認

```bash
# HTML レポート生成
pytest tests/unit --cov=src --cov-report=html

# ブラウザで確認
open htmlcov/index.html
```

### カバレッジ対象外

以下は意図的にテスト対象外:
- `src/main.py` - CLIエントリーポイント（手動テスト）
- FFmpeg実行部分 - 環境依存が大きい（統合テストで部分カバー）

---

## CI/CD統合

### GitHub Actions例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run unit tests
        run: pytest tests/unit -v --cov=src

      - name: Run integration tests
        run: pytest tests/integration -v

      - name: Run E2E tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: pytest tests/e2e -v
```

---

## トラブルシューティング

### よくある問題

**1. `ModuleNotFoundError: No module named 'src'`**

```bash
# プロジェクトルートから実行
cd /path/to/youtube-ai-v2
pytest tests/unit -v

# または PYTHONPATH設定
export PYTHONPATH=.
pytest tests/unit -v
```

**2. `pyttsx3` エラー（Linux）**

```bash
# 依存パッケージインストール
sudo apt-get install espeak espeak-data libespeak-dev
```

**3. FFmpeg not found**

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

**4. Gemini API rate limit**

```bash
# E2Eテストをスキップ
pytest tests/unit tests/integration -v
```

---

## ベストプラクティス

### テスト追加時のチェックリスト

- [ ] 新機能には必ずユニットテストを追加
- [ ] 外部API呼び出しはモック化
- [ ] エッジケース（エラー、境界値）をテスト
- [ ] テスト名は明確に（`test_what_when_expected`）
- [ ] フィクスチャを活用して重複排除
- [ ] `pytest -v` で全テスト通過確認

### テストの命名規則

```python
# Good
def test_script_generator_rejects_english_text():
    pass

def test_workflow_resumes_from_checkpoint():
    pass

# Bad
def test_script():  # 何をテストするか不明
    pass

def test1():  # 意味不明
    pass
```

---

## まとめ

- **合計**: 58+ テスト
- **ユニット**: 40+ テスト（<1秒）
- **統合**: 15+ テスト（数秒）
- **E2E**: 3 テスト（数分、要API key）

**推奨実行**:
```bash
# 開発時（高速）
pytest tests/unit -v

# コミット前（完全）
pytest tests/unit tests/integration -v

# リリース前（E2E含む）
pytest -v
```
