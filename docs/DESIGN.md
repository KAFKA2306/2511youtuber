# 設計仕様書 - YouTube AI Video Generator v2

**プロジェクト名**: YouTube AI Video Generator v2
**作成日**: 2025-10-10
**バージョン**: 2.0.0
**関連文書**: REQUIREMENTS.md

---

## 1. アーキテクチャ概要

### 1.1 設計哲学

**"Simple, Resilient, Modular"**

1. **Simple**: 5ステップで完結（前プロジェクト: 13ステップ）
2. **Resilient**: 障害時も部分的成功を保証
3. **Modular**: コンポーネント差し替え可能

### 1.2 システム構成図

```
┌─────────────────────────────────────────────────┐
│         Workflow Orchestrator                    │
│  (checkpoint-based, idempotent execution)       │
└────────┬────────────────────────────────────────┘
         │
         ├─► Step 1: NewsCollector ──► news.json
         │   (Perplexity → NewsAPI)
         │
         ├─► Step 2: ScriptGenerator ──► script.json
         │   (Gemini via LiteLLM + retry)
         │
         ├─► Step 3: AudioSynthesizer ──► audio.wav
         │   (VOICEVOX → pyttsx3)
         │
         ├─► Step 4: SubtitleFormatter ──► subtitles.srt
         │   (script.json timing validation)
         │
         └─► Step 5: VideoRenderer ──► video.mp4
             (FFmpeg: lavfi color + subtitles)

Output Structure:
runs/{run_id}/
  ├── news.json
  ├── script.json
  ├── audio.wav
  ├── subtitles.srt
  └── video.mp4
```

---

## 2. ディレクトリ構造

```
youtube-ai-v2/
├── docs/                    # ドキュメント
│   ├── REQUIREMENTS.md      # 要求仕様書
│   ├── DESIGN.md            # 設計仕様書（本文書）
│   └── ANTI_PATTERNS.md     # 旧プロジェクトの失敗パターン集
│
├── src/                     # ソースコード
│   ├── main.py              # エントリーポイント
│   ├── workflow.py          # ワークフローオーケストレータ
│   ├── models.py            # データモデル（Pydantic）
│   │
│   ├── steps/               # ワークフローステップ
│   │   ├── base.py          # 基底クラス
│   │   ├── news.py          # NewsCollector
│   │   ├── script.py        # ScriptGenerator
│   │   ├── audio.py         # AudioSynthesizer
│   │   ├── subtitle.py      # SubtitleFormatter
│   │   └── video.py         # VideoRenderer
│   │
│   ├── providers/           # 外部APIプロバイダ（プラグイン）
│   │   ├── base.py          # プロバイダ基底クラス
│   │   ├── llm.py           # LLMプロバイダ（Gemini）
│   │   ├── tts.py           # TTSプロバイダ（VOICEVOX, pyttsx3）
│   │   └── news.py          # ニュースプロバイダ（Perplexity, NewsAPI）
│   │
│   └── utils/               # ユーティリティ
│       ├── logger.py        # 構造化ログ
│       ├── config.py        # 設定ローダー
│       └── retry.py         # リトライロジック
│
├── tests/                   # テスト
│   ├── unit/                # ユニットテスト
│   ├── integration/         # 統合テスト
│   └── fixtures/            # テストデータ
│
├── config/                  # 設定ファイル
│   ├── default.yaml         # デフォルト設定
│   └── prompts.yaml         # LLM用の全てのプロンプトを集約（コード内部にはプロンプトがゼロ）
│   └── .env.example         # 環境変数テンプレート
│
├── runs/                    # 実行結果（gitignore）
│   └── {run_id}/            # 各実行の出力
│
├── pyproject.toml           # プロジェクト設定
├── uv.lock                  # 依存関係ロック
└── README.md                # プロジェクト概要
```

**前プロジェクトとの違い**:
- `app/` → `src/`（標準的な命名）
- `crew/`, `services/`, `config_prompts/` → 統合され `steps/`, `providers/` に集約
- `output/`, `cache/`, `temp/` → 単一の `runs/` ディレクトリに統一

---

## 3. コアコンポーネント設計

### 3.1 ワークフローオーケストレータ

**責務**: ステップの順次実行、チェックポイント管理、エラーハンドリング

```python
class WorkflowOrchestrator:
    def __init__(self, run_id: str, steps: List[Step]):
        self.run_id = run_id
        self.steps = steps
        self.state = WorkflowState.load_or_create(run_id)

    def execute(self) -> WorkflowResult:
        for step in self.steps:
            if step.name in self.state.completed_steps:
                logger.info(f"Skipping {step.name} (already completed)")
                continue

            try:
                output = step.execute(self.state.outputs)
                self.state.mark_completed(step.name, output)
                self.state.save()
            except CriticalError as e:
                logger.error(f"Critical error in {step.name}: {e}")
                return WorkflowResult(status="failed", error=str(e))
            except Exception as e:
                logger.warning(f"Non-critical error in {step.name}: {e}")
                if step.is_required:
                    return WorkflowResult(status="partial", error=str(e))

        return WorkflowResult(status="success")
```

**設計ポイント**:
- チェックポイントで中断・再開可能
- 各ステップの出力をファイルに保存（メモリ状態を持たない）
- Critical/Non-criticalエラーを区別

### 3.2 ステップ基底クラス

**責務**: 各ステップの共通インターフェース定義

```python
class Step(ABC):
    name: str
    is_required: bool = True

    @abstractmethod
    def execute(self, inputs: Dict[str, Path]) -> Path:
        pass

    def get_output_path(self, run_id: str) -> Path:
        return Path(f"runs/{run_id}/{self.output_filename}")

    def output_exists(self, run_id: str) -> bool:
        return self.get_output_path(run_id).exists()
```

**設計ポイント**:
- 各ステップは入力ファイルパス辞書を受け取り、出力ファイルパスを返す
- ステートレス（前のステップの実行結果に依存しない）
- 冪等性（同じ入力で何度実行しても同じ出力）

### 3.3 プロバイダ基底クラス

**責務**: 外部APIの抽象化、フォールバック管理

```python
class Provider(ABC):
    name: str
    priority: int  # 数字が小さいほど優先

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass

class ProviderChain:
    def __init__(self, providers: List[Provider]):
        self.providers = sorted(providers, key=lambda p: p.priority)

    def execute(self, **kwargs) -> Any:
        for provider in self.providers:
            if not provider.is_available():
                continue

            try:
                return provider.execute(**kwargs)
            except Exception as e:
                logger.warning(f"{provider.name} failed: {e}")

        raise AllProvidersFailedError()
```

**設計ポイント**:
- プロバイダは優先順位付きチェーンで管理
- 各プロバイダは独立してテスト可能
- 新規プロバイダは設定ファイルで追加可能

---

## 4. 各ステップの詳細設計

### 4.1 Step 1: NewsCollector

**入力**: なし
**出力**: `runs/{run_id}/news.json`

```python
class NewsCollector(Step):
    name = "collect_news"
    output_filename = "news.json"

    def execute(self, inputs: Dict[str, Path]) -> Path:
        providers = ProviderChain([
            PerplexityNewsProvider(priority=1),
            NewsAPIProvider(priority=2),
            DummyNewsProvider(priority=999)
        ])

        news_items = providers.execute(query="金融ニュース", count=3)
        output_path = self.get_output_path(self.run_id)

        with open(output_path, "w") as f:
            json.dump([item.dict() for item in news_items], f, ensure_ascii=False)

        return output_path
```

**データモデル**:
```python
class NewsItem(BaseModel):
    title: str
    summary: str
    url: str
    published_at: datetime
```

### 4.2 Step 2: ScriptGenerator

**入力**: `news.json`
**出力**: `runs/{run_id}/script.json`

```python
class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    @retry(max_attempts=3, backoff=2.0)
    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_items = self._load_news(inputs["news.json"])

        llm = GeminiProvider()
        raw_output = llm.generate(
            prompt=self._build_prompt(news_items),
            temperature=0.7
        )

        script = self._parse_and_validate(raw_output)
        output_path = self.get_output_path(self.run_id)

        with open(output_path, "w") as f:
            json.dump(script.dict(), f, ensure_ascii=False)

        return output_path

    def _parse_and_validate(self, raw: str) -> Script:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError:
            data = json.loads(raw)

        if isinstance(data, str):
            data = yaml.safe_load(data)

        script = Script(**data)

        if script.japanese_purity() < 1.0:
            raise ValueError(f"Japanese purity {script.japanese_purity()} < 1.0")

        return script
```

**LLM出力パース戦略**（前プロジェクトの失敗を回避）:
1. YAML → JSON → 再帰的YAML の3段階フォールバック
2. 日本語純度検証（英単語混入を拒否）:オンオフの機能や、読み上げに使われると困る記号を除去する機能などをオプション的に検討する
3. 構造検証（Pydanticで型チェック）

**データモデル**:
```python
class ScriptSegment(BaseModel):
    speaker: Literal["田中", "鈴木", "ナレーター"]
    text: str

    @validator("text")
    def validate_japanese(cls, v):
        if not is_pure_japanese(v):
            raise ValueError("Non-Japanese characters detected")
        return v

class Script(BaseModel):
    segments: List[ScriptSegment]
    total_duration_estimate: float

    def japanese_purity(self) -> float:
        total_chars = sum(len(seg.text) for seg in self.segments)
        japanese_chars = sum(
            len([c for c in seg.text if is_japanese_char(c)])
            for seg in self.segments
        )
        return japanese_chars / total_chars if total_chars > 0 else 0.0
```

### 4.3 Step 3: AudioSynthesizer

**入力**: `script.json`
**出力**: `runs/{run_id}/audio.wav`

```python
class AudioSynthesizer(Step):
    name = "synthesize_audio"
    output_filename = "audio.wav"

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script = self._load_script(inputs["script.json"])

        tts_chain = ProviderChain([
            VOICEVOXProvider(priority=1),
            Pyttsx3Provider(priority=2)
        ])

        audio_segments = []
        for segment in script.segments:
            audio = tts_chain.execute(
                text=segment.text,
                speaker=segment.speaker
            )
            audio_segments.append(audio)

        combined_audio = concatenate_audio(audio_segments)
        output_path = self.get_output_path(self.run_id)
        combined_audio.export(output_path, format="wav")

        return output_path
```

**話者マッピング**（設定ファイル駆動）:
```yaml
# config/default.yaml
tts:
　#### 読み上げスピードも定義する。基本的に1.6倍速で読み上げる設定にしておく。

  voicevox:
    speakers:
      田中: 11  # 玄野武宏（男性）
      鈴木: 8   # 春日部つむぎ（女性）
      ナレーター: 3  # ずんだもん

  pyttsx3:
    speakers:
      田中: {rate: 140, pitch: 50}
      鈴木: {rate: 160, pitch: 80}
      ナレーター: {rate: 150, pitch: 60}

```

### 4.4 Step 4: SubtitleFormatter

**入力**: `script.json`, `audio.wav`
**出力**: `runs/{run_id}/subtitles.srt`

```python
class SubtitleFormatter(Step):
    name = "prepare_subtitles"
    output_filename = "subtitles.srt"

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script = self._load_script(inputs["script.json"])
        audio_duration = get_audio_duration(inputs["audio.wav"])

        timestamps = self._calculate_timestamps(script, audio_duration)

        srt_content = self._generate_srt(script.segments, timestamps)
        output_path = self.get_output_path(self.run_id)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        return output_path

    def _calculate_timestamps(self, script: Script, audio_duration: float):
        total_chars = sum(len(seg.text) for seg in script.segments)
        current_time = 0.0
        timestamps = []

        for segment in script.segments:
            char_ratio = len(segment.text) / total_chars
            duration = audio_duration * char_ratio

            timestamps.append({
                "start": current_time,
                "end": current_time + duration,
                "text": segment.text
            })
            current_time += duration

        return timestamps
```

**設計ポイント**:
- Whisper STTを使わない（Phase 1では過剰）
- 文字数比率で時刻を均等配分（シンプルかつ十分）

### 4.5 Step 5: VideoRenderer

**入力**: `audio.wav`, `subtitles.srt`
**出力**: `runs/{run_id}/video.mp4`

```python
class VideoRenderer(Step):
    name = "render_video"
    output_filename = "video.mp4"

    def execute(self, inputs: Dict[str, Path]) -> Path:
        audio_path = inputs["audio.wav"]
        subtitle_path = inputs["subtitles.srt"]
        output_path = self.get_output_path(self.run_id)

        audio_duration = get_audio_duration(audio_path)

        video_stream = ffmpeg.input(
            f'color=c=0x193d5a:size=1920x1080:duration={audio_duration}:rate=25',
            f='lavfi'
        )

        video_stream = video_stream.filter(
            'subtitles',
            subtitle_path,
            force_style='FontName=Noto Sans CJK JP,FontSize=24'
        )

        audio_stream = ffmpeg.input(audio_path)

        output = ffmpeg.output(
            video_stream,
            audio_stream,
            output_path,
            vcodec='libx264',
            preset='medium',
            crf=23
        )

        ffmpeg.run(output, overwrite_output=True)

        return output_path
```

**設計ポイント**:
- 前プロジェクトの失敗（PNG loop hang）を回避: lavfi colorを直接使用
- パラメータ重複なし（前プロジェクトのBug #3を回避）
- シンプルな固定背景色（Phase 1では映像エフェクトなし）

---

## 5. データフロー

```
[User] ──► python main.py run
             │
             ├─► WorkflowOrchestrator
             │     │
             │     ├─► NewsCollector ──► news.json
             │     │     (API呼び出し、JSON保存)
             │     │
             │     ├─► ScriptGenerator ──► script.json
             │     │     (news.json読み込み、LLM呼び出し、YAML/JSONパース、検証、保存)
             │     │
             │     ├─► AudioSynthesizer ──► audio.wav
             │     │     (script.json読み込み、TTS呼び出し、音声結合、保存)
             │     │
             │     ├─► SubtitleFormatter ──► subtitles.srt
             │     │     (script.json + audio.wav読み込み、タイムスタンプ計算、SRT生成)
             │     │
             │     └─► VideoRenderer ──► video.mp4
             │           (audio.wav + subtitles.srt読み込み、FFmpeg実行)
             │
             └─► WorkflowResult
                   (success/failed/partial, outputs, errors)
```

**重要な設計判断**:
- 各ステップは前ステップの出力ファイルパスのみを受け取る
- メモリ内オブジェクトを共有しない（チェックポイント再開可能にするため）
- すべての中間生成物をファイルに保存（デバッグ容易性）

---

## 6. 設定管理

### 6.1 設定ファイル構造

```yaml
# config/default.yaml

workflow:
  default_run_dir: "runs"
  checkpoint_enabled: true

steps:
  news:
    count: 3
    query: "金融ニュース 最新"

  script:
    min_duration: 300  # 5分
    max_duration: 600  # 10分
    target_wow_score: 6.0
    retry_attempts: 3

  audio:
    sample_rate: 24000
    format: "wav"

  video:
    resolution: "1920x1080"
    fps: 25
    codec: "libx264"
    preset: "medium"
    crf: 23

providers:
  llm:
    gemini:
      model: "gemini-1.5-flash"
      temperature: 0.7
      max_tokens: 4000

  tts:
    voicevox:
      enabled: true
      url: "http://localhost:50021"
      speakers:
        田中: 11
        鈴木: 8
        ナレーター: 3

    pyttsx3:
      enabled: true
      speakers:
        田中: {rate: 140}
        鈴木: {rate: 160}
        ナレーター: {rate: 150}

  news:
    perplexity:
      enabled: true
      model: "llama-3.1-sonar-small-128k-online"

    newsapi:
      enabled: true
      country: "jp"
      category: "business"

logging:
  level: "INFO"
  format: "json"
  output: "logs/app.log"
```

### 6.2 環境変数（`.env`）

```bash
# API Keys
GEMINI_API_KEY=your-key-here
PERPLEXITY_API_KEY=your-key-here
NEWSAPI_KEY=your-key-here

# Optional: Multiple Gemini keys for rotation
GEMINI_API_KEY_2=another-key
GEMINI_API_KEY_3=yet-another-key
```

### 6.3 設定ローダー

```python
class Config(BaseModel):
    workflow: WorkflowConfig
    steps: StepsConfig
    providers: ProvidersConfig
    logging: LoggingConfig

    @classmethod
    def load(cls) -> "Config":
        config_path = Path("config/default.yaml")
        with open(config_path) as f:
            data = yaml.safe_load(f)

        load_dotenv()

        return cls(**data)
```

---

## 7. エラーハンドリング戦略

### 7.1 エラー分類

```python
class CriticalError(Exception):
    pass

class RetryableError(Exception):
    pass

class ValidationError(Exception):
    pass
```

### 7.2 リトライデコレータ

```python
def retry(max_attempts: int = 3, backoff: float = 2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except RetryableError as e:
                    if attempt == max_attempts - 1:
                        raise

                    wait_time = backoff ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        return wrapper
    return decorator
```

### 7.3 フォールバック戦略

| コンポーネント | 優先順位1 | 優先順位2 |
|--------------|----------|----------|
| ニュース収集 | Perplexity | NewsAPI |
| LLM | Gemini | - |
| TTS | VOICEVOX | pyttsx3 |

---

## 8. ログ設計

### 8.1 構造化ログ形式

```json
{
  "timestamp": "2025-10-10T12:34:56Z",
  "level": "INFO",
  "run_id": "20251010_123456",
  "step": "generate_script",
  "message": "Script generation completed",
  "metadata": {
    "duration_sec": 12.5,
    "segment_count": 15,
    "japanese_purity": 1.0
  }
}
```

### 8.2 ログレベル定義

- **DEBUG**: 開発時デバッグ情報（API呼び出しパラメータ等）
- **INFO**: 正常動作（ステップ完了通知）
- **WARNING**: 品質劣化だが継続可能（フォールバック発動等）
- **ERROR**: ステップ失敗（リトライ可能）
- **CRITICAL**: ワークフロー停止（全プロバイダ失敗等）

---

## 9. テスト設計

### 9.1 ユニットテスト

```python
# tests/unit/test_script_generator.py

def test_parse_yaml_output():
    generator = ScriptGenerator()
    raw = """
    segments:
      - speaker: 田中
        text: こんにちは
    """
    script = generator._parse_and_validate(raw)
    assert len(script.segments) == 1
    assert script.segments[0].speaker == "田中"

def test_reject_non_japanese():
    generator = ScriptGenerator()
    raw = """
    segments:
      - speaker: 田中
        text: Hello world
    """
    with pytest.raises(ValidationError):
        generator._parse_and_validate(raw)
```

### 9.2 統合テスト

```python
# tests/integration/test_workflow.py

@pytest.fixture
def mock_providers(mocker):
    mocker.patch("src.providers.llm.GeminiProvider.generate", return_value=MOCK_SCRIPT)
    mocker.patch("src.providers.tts.VOICEVOXProvider.execute", return_value=MOCK_AUDIO)
    mocker.patch("src.providers.news.PerplexityProvider.execute", return_value=MOCK_NEWS)

def test_full_workflow(mock_providers, tmp_path):
    orchestrator = WorkflowOrchestrator(run_id="test_001", run_dir=tmp_path)
    result = orchestrator.execute()

    assert result.status == "success"
    assert (tmp_path / "news.json").exists()
    assert (tmp_path / "script.json").exists()
    assert (tmp_path / "audio.wav").exists()
    assert (tmp_path / "video.mp4").exists()
```

### 9.3 E2Eテスト

```python
# tests/e2e/test_real_api.py

@pytest.mark.e2e
def test_real_gemini_api():
    if not os.getenv("RUN_E2E_TESTS"):
        pytest.skip("E2E tests disabled")

    llm = GeminiProvider()
    output = llm.generate(prompt="金融ニュースのスクリプトを生成してください", temperature=0.7)

    assert output is not None
    assert len(output) > 100
```

---

## 10. 依存関係

### 10.1 最小依存

```toml
[project]
name = "youtube-ai-v2"
version = "2.0.0"
requires-python = ">=3.11"

dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "litellm>=1.0",
    "ffmpeg-python>=0.2",
    "pyttsx3>=2.90",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.0",
    "ruff>=0.1",
]
```

**前プロジェクトとの違い**:
- CrewAI削除（過剰な抽象化）
- 直接LiteLLM使用（シンプル）
- ElevenLabs等の有料APIは除外（Phase 1では不要）

---

## 11. Phase 1実装計画

### 11.1 タスク分解

| タスク | ファイル | 推定時間 | 依存関係 |
|--------|---------|---------|---------|
| 1. プロジェクト構造作成 | - | 1h | - |
| 2. データモデル定義 | models.py | 2h | - |
| 3. 設定管理実装 | utils/config.py | 2h | - |
| 4. ログユーティリティ | utils/logger.py | 1h | - |
| 5. プロバイダ基底クラス | providers/base.py | 2h | - |
| 6. Geminiプロバイダ | providers/llm.py | 3h | 5 |
| 7. VOICEVOXプロバイダ | providers/tts.py | 3h | 5 |
| 8. ダミープロバイダ | providers/news.py | 1h | 5 |
| 9. ステップ基底クラス | steps/base.py | 2h | - |
| 10. NewsCollector | steps/news.py | 2h | 8,9 |
| 11. ScriptGenerator | steps/script.py | 4h | 6,9 |
| 12. AudioSynthesizer | steps/audio.py | 3h | 7,9 |
| 13. SubtitleFormatter | steps/subtitle.py | 2h | 9 |
| 14. VideoRenderer | steps/video.py | 3h | 9 |
| 15. ワークフローオーケストレータ | workflow.py | 4h | 9-14 |
| 16. CLIエントリーポイント | main.py | 2h | 15 |
| 17. ユニットテスト | tests/unit/* | 8h | 全体 |
| 18. 統合テスト | tests/integration/* | 4h | 全体 |
| 19. ドキュメント更新 | docs/* | 2h | - |
| 20. E2Eテスト | tests/e2e/* | 2h | 全体 |

**合計**: 約53時間 → 2週間（1日4時間作業）

### 11.2 マイルストーン

- **Week 1 End**: ステップ1-3完成（ニュース→スクリプト→音声）
- **Week 2 Mid**: ステップ4-5完成（字幕→動画）
- **Week 2 End**: テスト完成、ドキュメント更新

---

## 12. 成功指標

### 12.1 技術指標

- [ ] ワークフロー成功率: 95%以上（10回実行中9回以上成功）
- [ ] テストカバレッジ: 80%以上
- [ ] 統合テスト: 10件以上
- [ ] 平均実行時間: 10分以内

### 12.2 品質指標

- [ ] 日本語純度: 100%（英単語ゼロ）
- [ ] 動画生成成功: FFmpegエラーなし
- [ ] 音声品質: 3話者明確に区別可能

### 12.3 保守性指標

- [ ] 新規TTSプロバイダ追加: 1時間以内
- [ ] 新規LLMプロバイダ追加: 2時間以内
- [ ] 設定変更のみで話者変更可能

---

## 13. Phase 2以降の拡張計画

### 13.1 Phase 2: YouTube統合（+1週間）

```python
# src/steps/youtube.py
class YouTubeUploader(Step):
    name = "upload_youtube"
    is_required = False  # 失敗してもワークフローは成功扱い

    def execute(self, inputs: Dict[str, Path]) -> Path:
        video_path = inputs["video.mp4"]
        youtube_client = YouTubeClient()
        video_id = youtube_client.upload(video_path, title="...", description="...")

        output_path = self.get_output_path(self.run_id)
        with open(output_path, "w") as f:
            json.dump({"video_id": video_id}, f)

        return output_path
```

### 13.2 Phase 3: 映像エフェクト（+1週間）

```python
# src/providers/video_effect.py (プラグイン方式)
class KenBurnsEffect(VideoEffect):
    def apply(self, video_stream):
        return video_stream.filter('zoompan', z='min(zoom+0.0015,1.5)', d=125)

# config/default.yaml
video:
  effects:
    - type: "ken_burns"
      enabled: true
```

---

## 14. まとめ

### 14.1 前プロジェクトからの改善点

| 項目 | 前プロジェクト | 新プロジェクト |
|------|--------------|--------------|
| ステップ数 | 13 | 5 |
| 外部API必須 | 6 | 1（Gemini） |
| エラーハンドリング | 削除された | 完備 |
| テストカバレッジ | ~30% | 80%目標 |
| 統合テスト | 0件 | 10件以上 |
| チェックポイント | なし | あり |
| 部分的成功 | 不可 | 可能 |
| プロバイダ差し替え | 困難 | 容易 |

### 14.2 設計原則の再確認

1. **Simple**: 最小機能で動くシステム
2. **Resilient**: 障害時も部分的成功を保証
3. **Modular**: コンポーネント独立性
4. **Testable**: 高いテストカバレッジ
5. **Maintainable**: 明確なドキュメント

### 14.3 次のステップ

1. 本設計書のレビュー
2. 実装開始（タスク1から順次）
3. 継続的テスト実行
4. 週次進捗レビュー

---

**承認**: 未承認（ドラフト）
**レビュー担当**: -
**次回更新**: Phase 1完了時
