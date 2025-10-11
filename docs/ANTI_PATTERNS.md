# アンチパターン集 - 旧プロジェクトからの教訓

**作成日**: 2025-10-10
**元プロジェクト**: `/home/kafka/projects/2510youtuber` (旧版)
**目的**: 同じ失敗を二度と繰り返さないための警告集

---

## はじめに

このドキュメントは、旧プロジェクトで50時間以上かけても解決できなかった根本的な設計問題を記録し、新プロジェクトで同じ過ちを犯さないための教訓集です。

**重要**: これらは「小さなバグ」ではなく、「システムの根本的脆弱性」です。

---

## 1. アーキテクチャのアンチパターン

### ❌ アンチパターン1: 長大な逐次パイプライン

**旧プロジェクトの実装**:
```python
# app/main.py
for step in [step1, step2, ..., step13]:
    result = await step.execute(context)
    if not result.success:
        return FAILURE  # 全てのステップの成果物を破棄
```

**何が問題か**:
- 13ステップ × 各5%失敗率 = 約50%の全体失敗率
- ステップ12で失敗したら、ステップ1-11の成果物（音声、スクリプト等）も全て無駄になる
- デバッグが困難（どのステップで失敗したか追跡が難しい）

**なぜ起きたか**:
- 「機能追加 = ステップ追加」という安易な設計
- 失敗時のロールバック・再開機能を考慮していなかった
- 各ステップの独立性を意識していなかった

**正しいアプローチ**:
```python
# 新プロジェクト
for step in steps:
    if step.output_exists():
        continue  # チェックポイントでスキップ

    try:
        output = step.execute()
        step.save_output(output)  # 成功した成果物は必ず保存
    except CriticalError:
        break  # 中断しても他の成果物は保持
```

**教訓**:
- ステップ数は最小限に（5-7が限界）
- 各ステップは独立してテスト・実行可能にする
- チェックポイント機能は必須

---

### ❌ アンチパターン2: 外部API依存の蓄積

**旧プロジェクトの実装**:
```python
# 必須API: Gemini, ElevenLabs, Perplexity, NewsAPI, Pixabay, Pexels
# オプションAPI: YouTube, Google Sheets
# 合計8つの外部サービス
```

**何が問題か**:
- 複合障害率 = 1 - ∏(1 - 各APIの障害率)
- 例: 各API 95%可用性でも、8つで 0.95^8 = 66%（34%で何かしら失敗）
- APIレート制限、ネットワーク障害、サービス停止のいずれかで全体が止まる

**なぜ起きたか**:
- 「高品質」を追求して有料APIを次々に追加
- フォールバック戦略を後回しにした
- 各APIの可用性を楽観視

**正しいアプローチ**:
```python
# 必須API: 1つのみ（Gemini）
# フォールバック: 全てのコンポーネントにオフライン代替手段

class ProviderChain:
    def execute(self):
        for provider in [primary, secondary, offline_fallback]:
            try:
                return provider.execute()
            except:
                continue
        raise AllProvidersFailedError()
```

**教訓**:
- 外部API依存は最小限に（理想は1-2個）
- 全ての外部サービスにフォールバック戦略を用意
- オフライン動作可能な設計を優先

---

### ❌ アンチパターン3: ステートフルなワークフロー

**旧プロジェクトの実装**:
```python
class YouTubeWorkflow:
    def __init__(self):
        self.news_items = None
        self.script = None
        self.audio_path = None
        # ... メモリ内に状態を保持
```

**何が問題か**:
- ステップ8で失敗したら、ステップ1-7の状態はメモリ内のみ（再現不可）
- デバッグ時に途中ステップから再開できない
- 実行中にプロセスが落ちたら全てが失われる

**なぜ起きたか**:
- 「速度優先」でファイルI/Oを避けた
- チェックポイントの重要性を理解していなかった

**正しいアプローチ**:
```python
# 各ステップの出力を必ずファイルに保存
class Step:
    def execute(self, inputs: Dict[str, Path]) -> Path:
        output = self.process(inputs)
        output_path = self.get_output_path()
        output_path.write_text(json.dumps(output))
        return output_path  # メモリに保持しない
```

**教訓**:
- 全ての中間生成物をファイルに永続化
- メモリ内状態に依存しない
- いつでも途中から再開できる設計

---

## 2. エラーハンドリングのアンチパターン

### ❌ アンチパターン4: 「エラーを表面化するため」のtry-catch削除

**旧プロジェクトの実装**:
```python
# コミット c4f968c: "refactor: surface metadata storage failures"

# BEFORE:
try:
    self._save_to_sheets(data)
except Exception as e:
    logger.warning(f"Sheets failed: {e}")
    self._save_to_csv(data)  # フォールバック

# AFTER:
self._save_to_sheets(data)  # エラーは呼び出し元に伝播
```

**何が問題か**:
- Google Sheets障害時にワークフロー全体が停止
- "エラーを表面化"したつもりが、"システムを停止"させた
- オプション機能（Sheets保存）が必須機能になってしまった

**なぜ起きたか**:
- 「エラーハンドリングは問題を隠蔽する」という誤解
- エラーの重要度（Critical/Error/Warning）を区別していなかった
- "Fail fast"を"Fail always"と勘違い

**正しいアプローチ**:
```python
# エラーの重要度に応じた処理
try:
    self._save_to_sheets(data)
except Exception as e:
    logger.warning(f"Non-critical: Sheets failed: {e}")
    try:
        self._save_to_csv(data)
    except Exception as e2:
        logger.error(f"Critical: Both Sheets and CSV failed: {e2}")
        raise CriticalError("Cannot persist data")
```

**教訓**:
- エラーハンドリングは邪悪ではない、必須である
- エラーの重要度を明確に分類（Critical/Error/Warning）
- オプション機能の失敗でワークフロー全体を止めない

---

### ❌ アンチパターン5: LLM出力パースの楽観的実装

**旧プロジェクトの実装**:
```python
# app/services/script/generator.py:249

decoded = yaml.safe_load(text)
if isinstance(decoded, str):
    raise ValueError('YAML decoded to a string, not a mapping')
    # 以前は再帰的にパースしていたが削除された
```

**何が問題か**:
- LLMは時々YAML文字列を別のYAML文字列内に埋め込む
- この再帰的ラッピングを処理できず、`RecursionDepthExceeded`で停止
- 実際のログ: 4/5回の実行でこのエラーが発生

**なぜ起きたか**:
- LLMの出力を「常に正しい形式」と想定
- エッジケースのテストを書いていなかった
- リファクタリング時にテストなしで削除

**正しいアプローチ**:
```python
def parse_llm_output(text: str, max_depth: int = 3) -> dict:
    for _ in range(max_depth):
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            data = json.loads(text)  # YAMLダメならJSON

        if isinstance(data, dict):
            return data

        if isinstance(data, str):
            text = data  # 再帰的にパース
            continue

        raise ValueError(f"Unexpected type: {type(data)}")

    raise ValueError("Max recursion depth exceeded")
```

**教訓**:
- LLM出力は絶対に信用しない
- YAML/JSON/再帰ラッピング全てに対応
- 実際のLLM出力でテストを書く

---

### ❌ アンチパターン6: 暗黙的API契約違反

**旧プロジェクトの実装**:
```python
# app/metadata_storage.py:506
range_name = f"{sheet_name}!A1"  # ← BUG

sheets.values().append(
    spreadsheetId=spreadsheet_id,
    range=range_name,  # Google Sheets APIは "A:Z" を期待
    body={"values": rows}
).execute()
```

**何が問題か**:
- Google Sheets API の `.append()` は列範囲（`A:Z`）を要求
- セル参照（`A1`）を渡すと、エラーなく実行されるが何も保存されない
- サイレントな失敗＝デバッグ困難

**なぜ起きたか**:
- APIドキュメントを読んでいなかった
- テストで実際のAPI呼び出しを検証していなかった
- コード変更をコミット前に検証していなかった

**正しいアプローチ**:
```python
# APIの期待値を明示的に文書化
def append_to_sheet(sheet_name: str, rows: List[List[str]]):
    """
    Google Sheets APIのappend操作には列範囲が必要
    例: "Sheet1!A:Z" （正しい）
    例: "Sheet1!A1"  （間違い - サイレント失敗）
    """
    range_name = f"{sheet_name}!A:Z"  # 明示的に "A:Z" を使用

    sheets.values().append(
        range=range_name,
        body={"values": rows},
        valueInputOption="RAW"
    ).execute()
```

**教訓**:
- 外部APIの仕様を必ずドキュメントで確認
- APIの期待値をコメントで明記
- 統合テストで実際のAPI呼び出しを検証

---

## 3. テストのアンチパターン

### ❌ アンチパターン7: ユニットテストのみ、統合テストゼロ

**旧プロジェクトの実装**:
```bash
$ pytest tests/integration/
collected 0 items
```

**何が問題か**:
- 31個のユニットテストは全て通過
- しかし本番では4/5回失敗
- ステップ間の連携、API呼び出し、ファイルI/Oは未テスト

**なぜ起きたか**:
- 「ユニットテストだけで十分」という誤解
- 統合テストは「遅い」「面倒」と敬遠
- CI/CDがなく、手動テストに依存

**正しいアプローチ**:
```python
# tests/integration/test_workflow.py
@pytest.mark.integration
def test_workflow_with_mocked_apis(tmp_path, mock_gemini, mock_voicevox):
    orchestrator = WorkflowOrchestrator(run_dir=tmp_path)
    result = orchestrator.execute()

    assert result.status == "success"
    assert (tmp_path / "news.json").exists()
    assert (tmp_path / "script.json").exists()
    assert (tmp_path / "video.mp4").exists()
```

**教訓**:
- ユニットテスト: 80%、統合テスト: 15%、E2E: 5%のバランス
- 統合テストは必須（ステップ間連携をテスト）
- CI/CDで自動実行

---

### ❌ アンチパターン8: リファクタリング時のテスト不足

**旧プロジェクトの実装**:
```bash
# コミット 6cf55df: "refactor: migrate from JSON to YAML"
# - 再帰的YAMLパースを削除
# - テスト追加なし
# - 結果: 本番で RecursionDepthExceeded
```

**何が問題か**:
- リファクタリング時にテストを書かなかった
- 既存のテストがエッジケースをカバーしていなかった
- 本番環境で初めてバグ発見

**なぜ起きたか**:
- 「動いているから大丈夫」という楽観主義
- コードレビューなし
- CI/CDなし

**正しいアプローチ**:
```python
# リファクタリング前にテスト追加
def test_yaml_recursive_wrapping():
    """LLMが時々YAMLを文字列内に埋め込むケース"""
    text = '''
    "segments:
      - speaker: 春日部つむぎ
        text: こんにちは"
    '''
    result = parse_llm_output(text)
    assert result["segments"][0]["speaker"] == "春日部つむぎ"
```

**教訓**:
- リファクタリング前にエッジケーステストを追加
- コードレビュー必須
- CI/CDで自動検証

---

## 4. プロセスのアンチパターン

### ❌ アンチパターン9: コミット前検証なし

**旧プロジェクトの実装**:
```bash
# Gitフックなし
# CI/CDなし
# ローカルで動けばコミット
```

**何が問題か**:
- 3つのバグのうち2つは未コミットのローカル変更
- コミット時にテストを実行していなかった
- 他人（未来の自分）が同じコードを動かせない保証がない

**なぜ起きたか**:
- 「自分しか使わないから大丈夫」という過信
- プロセス整備を後回しにした

**正しいアプローチ**:
```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit -v || exit 1
ruff check . || exit 1
```

**教訓**:
- Git pre-commitフック必須
- CI/CD整備（GitHub Actions等）
- 「動く」の定義 = テストが通る

---

### ❌ アンチパターン10: ドキュメント後回し

**旧プロジェクトの実装**:
```python
# Google Sheets APIの期待値についてコメントなし
range_name = f"{sheet_name}!A1"  # なぜA1? A:Zではダメ?
```

**何が問題か**:
- 3ヶ月後の自分がコードを理解できない
- バグ修正時に「なぜこう書いたか」が不明
- APIの期待値が暗黙的

**なぜ起きたか**:
- 「コードが読めればドキュメント不要」という誤解
- 「後で書く」と先延ばし

**正しいアプローチ**:
```python
def append_to_sheet(sheet_name: str, rows: List[List[str]]):
    """
    Google Sheets APIに行を追加

    重要: append操作には列範囲（A:Z）が必要
    セル参照（A1）を使うとサイレント失敗する
    参考: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/append
    """
    range_name = f"{sheet_name}!A:Z"
```

**教訓**:
- コードと同時にドキュメント記述
- APIの期待値を必ず明記
- 「なぜ」を記録する

---

## 5. 設計のアンチパターン

### ❌ アンチパターン11: 機能過多（Feature Creep）

**旧プロジェクトの実装**:
- 13ステップワークフロー
- 7つのCrewAIエージェント
- 8つの外部API連携
- Google Sheets 3タブ連携
- フィードバックループ分析
- B-roll映像生成
- サムネイル生成
- ...

**何が問題か**:
- 複雑すぎてデバッグ不可能
- どこかが必ず壊れている状態が常態化
- 「動画を生成する」というコア機能が埋もれる

**なぜ起きたか**:
- 「もっと良くしたい」という欲求
- MVPの概念がなかった
- 機能追加の閾値が低すぎた

**正しいアプローチ**:
```
Phase 1: MVPのみ実装
  - ニュース収集
  - スクリプト生成
  - 音声合成
  - 動画生成
  - ローカル保存
  ↓ 動作確認
Phase 2: 拡張機能（オプション）
  - YouTube自動アップロード
  - メタデータ分析
  - 映像エフェクト
```

**教訓**:
- まず動く最小システムを完成させる
- 拡張機能は後から追加
- 「これは本当に必要か?」を常に自問

---

### ❌ アンチパターン12: 密結合

**旧プロジェクトの実装**:
```python
# app/crew/flows.py
class VideoScriptFlow(Flow):
    def __init__(self):
        self.agents = create_all_agents()  # 7エージェント全て依存
        self.tasks = create_all_tasks()    # 全タスク依存
```

**何が問題か**:
- エージェント1つを差し替えるだけで全体が壊れる
- TTSプロバイダを変更すると音声処理全体を書き直し
- モジュール単位のテストが困難

**なぜ起きたか**:
- インターフェース設計をしなかった
- 具象クラスに直接依存
- 「動けば良い」で設計をスキップ

**正しいアプローチ**:
```python
# プロバイダインターフェース
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, speaker: str) -> AudioSegment:
        pass

# 実装は差し替え可能
class VOICEVOXProvider(TTSProvider):
    def synthesize(self, text, speaker):
        # VOICEVOX固有の実装

class Pyttsx3Provider(TTSProvider):
    def synthesize(self, text, speaker):
        # pyttsx3固有の実装
```

**教訓**:
- 抽象インターフェースに依存
- 具象クラスは差し替え可能に
- SOLID原則の遵守

---

### ❌ アンチパターン13: 設定のハードコーディング

**旧プロジェクトの実装**:
```python
# app/tts/providers.py
VOICEVOX_SPEAKERS = {
    "春日部つむぎ": 11,  # ハードコーディング
    "ずんだもん": 8,
}

# app/video.py
VIDEO_WIDTH = 1920  # ハードコーディング
VIDEO_HEIGHT = 1080
```

**何が問題か**:
- 話者IDを変更するにはコード修正が必要
- 解像度変更にコード変更が必要
- 設定ファイルとコードが分離していない

**なぜ起きたか**:
- 「とりあえず動かす」が優先
- 設定ファイル設計を後回し

**正しいアプローチ**:
```yaml
# config/default.yaml
tts:
  voicevox:
    speakers:
      春日部つむぎ: 11
      ずんだもん: 8

video:
  resolution: "1920x1080"
  fps: 25
```

```python
# src/utils/config.py
config = Config.load()
speaker_id = config.tts.voicevox.speakers[speaker_name]
```

**教訓**:
- 全ての設定を外部ファイル化
- コード変更なしで挙動変更可能に
- 環境変数とYAMLで設定管理

---

## 6. FFmpegのアンチパターン

### ❌ アンチパターン14: パラメータ重複指定

**旧プロジェクトの実装**:
```python
# app/video.py
def _run_ffmpeg(self, stream):
    cmd = stream.compile()  # 1回目のコンパイル
    ffmpeg.run(stream, ...)  # 2回目のコンパイル（内部で実行）
```

**何が問題か**:
- ストリームオブジェクトを2回コンパイル
- 無駄なCPU使用
- 状態が変わる可能性（非冪等）

**なぜ起きたか**:
- `ffmpeg.run()`の内部挙動を理解していなかった
- デバッグログのために追加したが副作用を考慮せず

**正しいアプローチ**:
```python
def _run_ffmpeg(self, stream):
    try:
        ffmpeg.run(stream, ...)  # コンパイルは内部で1回のみ
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg failed: {e.stderr.decode()}")
        raise
```

**教訓**:
- ライブラリの内部挙動を理解してから使う
- デバッグ用コード追加時も副作用を考慮

---

### ❌ アンチパターン15: PNG背景のFFmpegループハング

**旧プロジェクトの実装**:
```python
# app/video.py:296
stream = ffmpeg.input(bg_image_path, loop=1, framerate=fps, t=duration, f='image2')
```

**何が問題か**:
- FFmpegが `-loop 1` パラメータでPNG画像を読む際にハング
- フレーム1で停止、15,853フレームのうち0.006%のみ処理
- タイムアウトなしで無限待機

**なぜ起きたか**:
- PNG + loop の組み合わせの既知の問題を知らなかった
- タイムアウト処理がなかった

**正しいアプローチ**:
```python
# lavfi colorソースを直接使用（PNGファイル不要）
stream = ffmpeg.input(
    f'color=c=0x193d5a:size=1920x1080:duration={duration}:rate={fps}',
    f='lavfi'
)
```

**教訓**:
- FFmpegのエッジケースを事前調査
- タイムアウト必須
- シンプルな方法を優先（PNGファイル生成不要）

---

## 7. CrewAIのアンチパターン

### ❌ アンチパターン16: 過剰なエージェント抽象化

**旧プロジェクトの実装**:
```python
# app/crew/flows.py
agents = [
    DeepNewsAnalyzer(),
    CuriosityGapResearcher(),
    EmotionalStoryArchitect(),
    ScriptWriter(),
    EngagementOptimizer(),
    QualityGuardian(),
    JapanesePurityPolisher()
]  # 7エージェント
```

**何が問題か**:
- 7エージェントが順次実行で遅い
- 各エージェントの責任範囲が不明瞭
- デバッグ時にどのエージェントが悪いか特定困難

**なぜ起きたか**:
- 「エージェント = 機能分割」という誤解
- CrewAIの使い方を理解せずに採用

**正しいアプローチ**:
```python
# 単一のLLM呼び出しで十分
llm = GeminiProvider()
script = llm.generate(
    prompt="""
    以下のニュースから5-10分の対話形式スクリプトを生成してください。
    話者: 春日部つむぎ、ずんだもん、玄野武宏
    日本語のみ使用してください。
    """,
    temperature=0.7
)
```

**教訓**:
- 複雑なフレームワークは本当に必要か検討
- シンプルな方法で十分なら採用しない
- 抽象化は慎重に

---

## 8. まとめ: 失敗の本質

### 根本原因

旧プロジェクトの失敗は「小さなバグの集積」ではなく、**設計哲学の欠如**が原因:

1. **レジリエンス設計の欠如**: 障害を想定していない楽観的設計
2. **テストの軽視**: 「動いているから大丈夫」という過信
3. **プロセスの不在**: CI/CD、コードレビュー、ドキュメント管理なし
4. **機能過多**: MVPの概念なく、機能を追加し続けた
5. **責任範囲の不明確**: モジュール境界が曖昧で密結合

### 新プロジェクトで絶対に守るべき原則

1. **Simple**: 5ステップで完結、外部API依存最小化
2. **Resilient**: 全てのステップにフォールバック、チェックポイント機能
3. **Modular**: 各コンポーネントは独立してテスト・差し替え可能
4. **Tested**: ユニット80%、統合10件以上、E2Eテスト
5. **Documented**: コードと同時にドキュメント記述

### 行動指針

- [ ] 新機能追加時: 「これは本当に必要か？」を自問
- [ ] エラーハンドリング: 「Critical/Error/Warning」を明確に分類
- [ ] API呼び出し: 必ずtry-catchで囲む
- [ ] リファクタリング: テストを書いてから実行
- [ ] コミット前: テスト実行、linting、ドキュメント確認

---

**このドキュメントの目的**: 同じ失敗を二度と繰り返さない

**次に読むべき文書**: DESIGN.md（新プロジェクトの設計仕様書）
