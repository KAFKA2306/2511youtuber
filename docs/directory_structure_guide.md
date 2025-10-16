# リポジトリ全体の見取り図と設計意図ガイド

## 1. このドキュメントの目的
このリポジトリは「最新の金融ニュースをもとに日本語の動画を自動生成する」ワークフローを包含しています。本ガイドは、非技術者でも全体像と各ディレクトリ・ファイルの役割を理解できるよう、目的・命名・連携関係を丁寧に解説します。READMEと既存ドキュメントではワークフローやセットアップ手順が概説されていますが、ディレクトリごとの構造や設計意図を一気通貫で把握できる資料がなかったため、本ドキュメントがそのギャップを埋めます。【F:README.md†L1-L52】【F:docs/system_overview.md†L1-L40】

## 2. ルート直下の主要ファイルとディレクトリ
```
├── apps/
├── config/
├── docs/
├── scripts/
├── src/
├── tests/
├── assets/
├── README.md
├── pyproject.toml
├── pytest.ini
└── （実行時に生成）runs/
```
READMEには上記の概要が記載されており、ワークフロー全体の入り口・構成要素を俯瞰できます。【F:README.md†L39-L48】以下、各要素を順番に説明します。

### 2.1 README.md
- プロジェクトの狙い、実行方法、ステップごとの成果物が一覧化されています。【F:README.md†L1-L33】
- 「Workflow summary」表は、後述する`src/steps/`配下のクラスと生成ファイル名の対応表になっており、パイプラインの進行を理解する地図です。【F:README.md†L23-L32】

### 2.2 pyproject.toml
- Python 3.11以上を前提に、Pydantic・FFmpeg・Discord・Google API クライアントなどの依存関係を定義しています。音声合成（VOICEVOX）、動画編集（ffmpeg-python）、SNS投稿（tweepy）まで必要なライブラリが明示されているため、どの領域の機能が含まれているかを推測できます。【F:pyproject.toml†L1-L59】
- `tool.hatch.build`設定で配布物に含めるディレクトリを限定しており、`src/`以下がパッケージ化対象であること、`config/`や`docs/`も配布物に含める意図が読み取れます。【F:pyproject.toml†L36-L41】

### 2.3 pytest.ini
- テストは`tests/`配下のみを走査し、`unit`/`integration`/`e2e`というマーカーで粒度を管理する運用になっています。これにより、外部APIを呼ぶ重いテストと軽いテストを明確に区別できます。【F:pytest.ini†L1-L15】

### 2.4 runs/（実行時に生成）
- CLI実行時に`runs/<run_id>/`が作成され、ステップごとの成果物と`state.json`が保存されます。後述する`WorkflowOrchestrator`と`WorkflowState`がこの仕組みを支えています。【F:apps/youtube/cli.py†L33-L67】【F:src/core/state.py†L11-L46】

## 3. config/ ディレクトリ
構成ファイルとプロンプト、環境変数テンプレートを収める設定の中枢です。

### 3.1 default.yaml
- `steps`セクションはパイプライン各段のパラメータを定義します。たとえば字幕幅(`subtitle`)、動画レンダリング設定(`video`)、サムネイル装飾(`thumbnail`)など、後述する各ステップクラスが参照する値が格納されています。【F:config/default.yaml†L5-L149】
- `providers`セクションにはLLM（Gemini）、音声合成（VOICEVOX）、ニュース収集（Perplexity）の接続情報が集約されています。`manager_script`に`scripts/voicevox_manager.sh`が指定されている点からも、スクリプトと設定が密接に連携していることが分かります。【F:config/default.yaml†L151-L176】
- `logging`セクションでログ出力形式を`json`に固定しており、運用時のログ解析を意識した設計です。【F:config/default.yaml†L179-L181】

### 3.2 prompts.yaml
- ニュース収集・台本生成・メタデータ生成それぞれのプロンプトが日本語で詳細に記述されています。特にスクリプト用のテンプレートでは、キャラクター名（春日部つむぎ・ずんだもん等）が指定されており、後述の`ScriptGenerator`がこの情報を埋め込んでLLMに渡します。【F:config/prompts.yaml†L1-L122】

### 3.3 .env.example
- 必須のGemini APIキーと、任意のPerplexity・X（Twitter）系キーの置き場を示したサンプルです。実際の秘密情報はコミットせず、`src/utils/secrets.py`がこのファイルを読み込んで複数キーを統合します。【F:config/.env.example†L1-L24】【F:src/utils/secrets.py†L6-L35】

## 4. apps/ ディレクトリ
アプリケーションごとのエントリーポイントを配置します。現状はYouTubeワークフローのみが存在します。

### 4.1 apps/youtube/cli.py
- `run`関数がパイプラインの司令塔です。設定を読み込み、ユーザーから渡されたニュース検索キーワードを上書きし、`WorkflowOrchestrator`に渡すステップ一覧を構築します。【F:apps/youtube/cli.py†L27-L115】
- `_build_steps`は、設定に従って`NewsCollector`や`VideoRenderer`などの必須ステップに加え、メタデータ解析・サムネイル生成・各種投稿ステップを条件付きで追加します。関数名は「ステップ一覧を組み立てる」意図そのもので、設定値を辞書化する工程も読み取れます。【F:apps/youtube/cli.py†L72-L166】
- 実行結果をロギングし、成功／部分成功／失敗で異なるメッセージを表示する処理もここにまとまっているため、CLI利用者の体験設計が`run`関数で完結しています。【F:apps/youtube/cli.py†L46-L69】

### 4.2 apps/__init__.py
- 空ファイルで、将来のアプリ追加時にPythonパッケージとして扱えるようにしています。

### 4.3 apps/youtube/__init__.py
- `run`関数を外部から直接インポートできるよう再エクスポートしています。`src/main.py`はこれを利用してCLIを起動します。【F:apps/youtube/__init__.py†L1-L1】【F:src/main.py†L1-L23】

## 5. src/ ディレクトリ
実装の中枢です。`main.py`→`apps`→`core`/`steps`/`providers`/`utils`という層構造で組み上げられています。

### 5.1 main.py
- `parse_args`が`--news-query`オプションを受け取り、`.env`ファイルを読み込んだ上で`apps.youtube.run`へ処理を委譲します。エントリーポイントとして必要最小限の責務に絞られています。【F:src/main.py†L1-L27】

### 5.2 core/
#### 5.2.1 step.py
- すべてのステップが継承する抽象クラス`Step`を定義。`name`と`output_filename`というクラス属性が必須で、`run`メソッドが「既に成果物が存在すれば再実行しない」という再実行耐性を実現します。`StepExecutionError`は成果物が生成されなかった場合にエラーを出すための名前付き例外です。【F:src/core/step.py†L8-L36】

#### 5.2.2 orchestrator.py
- `WorkflowOrchestrator`はステップを順番に実行し、完了後すぐに`WorkflowState`を保存します。`run_id`ごとに`runs/<run_id>/state.json`が更新される設計で、途中から再開する際は`completed_steps`を参照してスキップします。【F:src/core/orchestrator.py†L11-L36】

#### 5.2.3 state.py
- `WorkflowState`はPydanticモデルとして実装され、JSONファイルとの相互変換を簡潔にしています。`mark_completed`/`mark_success`/`mark_failed`といったメソッド名が状態遷移を自己説明しており、各ステップの出力パスも併せて記録されます。【F:src/core/state.py†L11-L54】
- `WorkflowResult`は最終的な実行結果を表すデータモデルで、CLIがユーザーに表示する情報の型となります。【F:src/core/state.py†L49-L54】

#### 5.2.4 io_utils.py と media_utils.py
- `io_utils`はJSON読み込み・テキスト書き込み・ファイル存在チェックを集約しており、ステップ実装が重複コードを書かずに済むよう配慮されています。【F:src/core/io_utils.py†L10-L32】
- `media_utils`は音声長の算出、FFmpegバイナリ検出、パス整形を担当します。動画レンダリングや字幕焼き込みで必要な周辺機能を切り出しており、名称が用途をそのまま表しています。【F:src/core/media_utils.py†L7-L20】

### 5.3 models.py
- `NewsItem`（ニュース記事）、`ScriptSegment`（台本の発話単位）、`Script`（全体の構成）といったデータモデルが定義され、型付けされたデータ構造を共有します。クラス名は取り扱う実体を直接示しているため、読むだけで意図が伝わります。【F:src/models.py†L7-L23】

### 5.4 steps/
各ステップは`Step`を継承し、`name`と`output_filename`が成果物ファイル名を明示します。ステップ名は後段の`state.json`キーや設定ファイル内の参照名としても利用されます。

- **NewsCollector (`collect_news` → `news.json`)**: Perplexity/Geminiのプロバイダーを設定に応じて組み合わせ、ニュースJSONを生成します。【F:src/steps/news.py†L11-L51】
- **ScriptGenerator (`generate_script` → `script.json`)**: ニュース要約と話者プロファイルをプロンプトに埋め込み、Geminiから返った結果を厳格にパースします。過去Runからの文脈引き継ぎや話者名抽出など、命名から「台本生成のためのステップ」と分かる設計です。【F:src/steps/script.py†L43-L204】
- **AudioSynthesizer (`synthesize_audio` → `audio.wav`)**: Scriptを読み込み、VOICEVOX APIで各セグメントを音声化し連結します。`speaker_aliases`による名前ゆれ吸収など、音声合成特有の責務が集中しています。【F:src/steps/audio.py†L10-L37】【F:src/providers/tts.py†L12-L86】
- **SubtitleFormatter (`prepare_subtitles` → `subtitles.srt`)**: 音声長に合わせて各セグメントの表示時間を割り付け、日本語の文字幅を考慮した改行を施します。`max_chars_per_line`は設定ファイルから算出され、視認性を担保します。【F:src/steps/subtitle.py†L11-L109】【F:apps/youtube/cli.py†L100-L108】
- **VideoRenderer (`render_video` → `video.mp4`)**: 単色背景の動画ストリームを生成し、動画効果パイプラインと字幕焼き込みを適用してから音声と合成します。FFmpegコマンドの組み立てはここに集約されています。【F:src/steps/video.py†L14-L84】
- **MetadataAnalyzer (`analyze_metadata` → `metadata.json`)**: 台本やニュースを読み取り、LLMまたはフォールバックロジックでSEO向けタイトル・説明・タグを生成します。`use_llm`フラグでLLM利用可否を切り替えられる設計です。【F:src/steps/metadata.py†L16-L167】
- **ThumbnailGenerator (`generate_thumbnail` → `thumbnail.png`)**: 事前定義の配色プリセットから背景を作成し、タイトル・サブタイトル・キャラクター画像をレイアウトします。`is_required = False`により欠損してもパイプラインが継続できる設計です。【F:src/steps/thumbnail.py†L14-L240】
- **YouTubeUploader / TwitterPoster / PodcastExporter / BuzzsproutUploader**: それぞれYouTube公開、X(Twitter)投稿、Podcastフィード生成、Buzzsproutアップロードを担当する任意ステップです。設定で有効化された場合のみ`_build_steps`に追加されます。【F:src/steps/youtube.py†L11-L59】【F:src/steps/twitter.py†L12-L64】【F:src/steps/podcast.py†L14-L61】【F:src/steps/buzzsprout.py†L14-L65】【F:apps/youtube/cli.py†L117-L165】

### 5.5 providers/
外部サービスとの橋渡しを行うモジュール群です。

- **base.py**: `Provider`プロトコルと`ProviderChain`を定義し、複数プロバイダーを優先度順に試行するフォールバック機構を提供します。【F:src/providers/base.py†L1-L41】
- **news.py**: Perplexity/Gemini APIを呼び出し、プロンプトに合わせてJSONを整形します。`priority`属性でフォールバック順を制御し、`load_prompts`によって共通テンプレートを参照しています。【F:src/providers/news.py†L15-L135】
- **llm.py**: Gemini呼び出しの共通クラス。モデル名やトークン長を設定ファイルから補完し、503エラー時にフォールバックモデルへ切り替えるリトライロジックを備えます。【F:src/providers/llm.py†L11-L142】
- **tts.py**: VOICEVOXエンジンにテキストを送り、AudioSegmentで返却します。別名対応（エイリアス）や自動起動 (`auto_start`) の仕組みがあり、設定ファイルのスピーカーIDと一致させる設計です。【F:src/providers/tts.py†L12-L86】【F:config/default.yaml†L159-L168】
- **video_effects.py**: FFmpegフィルターをオブジェクト指向で定義。Ken Burns効果やキャラクターオーバーレイなど、動画演出を`VideoEffectPipeline`として差し替え可能にしています。【F:src/providers/video_effects.py†L1-L164】
- **twitter.py / youtube.py**: それぞれtweepy・Google APIクライアントをラップし、環境変数・秘密情報の読み込みやドライラン対応を提供します。関数名やクラス名は使い方を直感的に示すよう付けられています。【F:src/providers/twitter.py†L1-L115】【F:src/providers/youtube.py†L22-L170】

### 5.6 utils/
補助的なユーティリティ群です。

- **config.py**: Pydanticモデルで設定ファイルを厳密に検証し、`Config.load()`でYAMLを読み込みます。ステップやプロバイダーごとの型が分割定義されており、設定値の意味がクラス名から読み取れます。【F:src/utils/config.py†L12-L300】
- **logger.py**: ロガー初期化を一箇所にまとめ、CLI・プロバイダーで一貫したログ形式を使えるようにします。【F:src/utils/logger.py†L1-L7】
- **secrets.py**: 環境変数と`.env`ファイルの両方から秘密鍵を読み集め、重複を排除して返します。`load_secret_values`という関数名により用途が明確です。【F:src/utils/secrets.py†L6-L35】
- **discord.py / discord_config.py**: Discord通知用のWebhook解決と設定ファイル読み込みを担当します。ワークフロー完了後にニュースまとめや動画URLを送る`post_run_summary`は、`apps/youtube/cli.py`から呼び出されます。【F:src/utils/discord.py†L11-L77】【F:apps/youtube/cli.py†L40-L45】【F:src/utils/discord_config.py†L10-L18】

## 6. scripts/ ディレクトリ
- **voicevox_manager.sh**: DockerコンテナとしてVOICEVOXエンジンを起動・停止・ヘルスチェックするユーティリティ。設定ファイルの`manager_script`と連携し、自動起動フローをサポートします。【F:scripts/voicevox_manager.sh†L3-L106】【F:config/default.yaml†L159-L164】
- **inspect_tree.py**: Pythonファイルの行数やインポート依存を集計する分析ツール。リファクタリング時に負債を可視化する目的で整備されています。【F:scripts/inspect_tree.py†L1-L128】
- **discord_news_bot.py**: Discordスラッシュコマンドからニュース収集ワークフローを起動するBot。環境変数読み込み→スレッド作成→非同期コマンド登録までを自動化します。【F:scripts/discord_news_bot.py†L1-L63】
- その他のシェルスクリプト（`run_workflow_cron.sh`など）は運用自動化用のフックとして配置されており、必要に応じてカスタマイズできます。

## 7. docs/ ディレクトリ
- **system_overview.md**: アーキテクチャとデフォルトパイプラインの説明があり、`WorkflowOrchestrator`や各ステップの役割が整理されています。【F:docs/system_overview.md†L1-L40】
- **operations.md**: 環境構築・ワークフロー実行・テスト運用の手引き。`config/default.yaml`に沿ったトグル操作の説明が載っており、非エンジニアでも設定変更の影響が分かります。【F:docs/operations.md†L3-L37】
- 本ドキュメント（`directory_structure_guide.md`）を加えることで、構成理解→運用→アーキテクチャの三層ドキュメント体系が完成します。

## 8. assets/ ディレクトリ
- フォントやキャラクター画像が格納されます。設定ファイルで参照されている`assets/fonts/ZenMaruGothic-Bold.ttf`や春日部つむぎ立ち絵などを差し替えることで、動画やサムネイルのブランド調整が可能です。【F:config/default.yaml†L55-L117】

## 9. tests/ ディレクトリ
テストコードはディレクトリ構造をなぞる形で配置され、主要なロジックが検証されています。

- `test_workflow_core.py`: オーケストレーターが成果物を再利用する挙動、成果物未生成時の例外など、基盤ロジックを検証します。【F:tests/test_workflow_core.py†L12-L70】
- `test_provider_chain.py`: プロバイダーフォールバックの優先度や失敗時例外を確認し、外部API呼び出しの堅牢性を担保します。【F:tests/test_provider_chain.py†L8-L74】
- `test_news_step.py`: ニュースステップが設定通りのプロバイダーを構築するかをチェックし、設定変更の影響を早期検知します。【F:tests/test_news_step.py†L11-L49】
- `test_video_effects_pipeline.py`: 動画効果の組み立て・座標計算を検証し、FFmpegフィルターの式が変わった際の破壊的変更を防ぎます。【F:tests/test_video_effects_pipeline.py†L13-L51】
- `test_config_and_secrets.py`: 設定モデルの往復読み込みと秘密情報マージロジックを確認し、設定ファイルの整合性を保証します。【F:tests/test_config_and_secrets.py†L12-L169】

## 10. runs/ ディレクトリと成果物命名規則
- ステップ名と`output_filename`は1対1で対応しており、`runs/<run_id>/`配下で成果物が即座に見分けられます。例：`collect_news`→`news.json`、`render_video`→`video.mp4`。`state.json`には完了済みステップと生成ファイルのパスが記録され、同一Runの再実行時は自動でスキップされます。【F:src/core/step.py†L23-L36】【F:src/core/state.py†L11-L46】
- `post_run_summary`がDiscordへ通知する際も、ステップ名で成果物を参照してURLやサマリーを抽出します。命名規則が通知ロジックと連携している好例です。【F:src/utils/discord.py†L48-L77】

## 11. 設計意図のまとめ
1. **パイプライン設計**: `Step`抽象クラス＋`WorkflowOrchestrator`により、成果物キャッシュと失敗復旧を自動化。非同期処理ではなく逐次処理を採用することで、デバッグしやすさを優先しています。【F:src/core/step.py†L23-L36】【F:src/core/orchestrator.py†L18-L36】
2. **設定駆動**: すべての可変値は`config/default.yaml`とPydanticモデルに集約し、コード側は辞書から値を取り出すだけに留めています。名前付きクラス（`VideoStepConfig`など）が意味を説明するため、非エンジニアでも「どの項目を変えると何が起こるか」を推測しやすくなっています。【F:src/utils/config.py†L109-L223】【F:config/default.yaml†L5-L176】
3. **プロバイダー分離**: 外部サービスごとに`providers/`でラップし、ステップからは高水準メソッド（`execute`や`upload`）を呼ぶだけで済むようにしています。エラーリトライやDry-run対応はプロバイダー層に閉じ込められているため、上位ステップはシンプルなフローに集中できます。【F:src/providers/llm.py†L56-L142】【F:src/providers/twitter.py†L42-L115】
4. **運用補助**: Discord通知、Voicevox管理スクリプト、テストマーカーなど運用を支援する仕組みが整備されています。名前から用途が推測できる命名（例:`post_run_summary`、`voicevox_manager.sh`）により、非技術者でも設定ファイルから関連ツールを見つけられます。【F:src/utils/discord.py†L48-L77】【F:scripts/voicevox_manager.sh†L3-L106】

本ガイドを参考にディレクトリ構造を辿れば、初見の方でも「どのファイルを編集すればどの成果物が変わるのか」「名前が示す機能は何か」を自信を持って判断できるようになります。
