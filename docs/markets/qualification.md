# 資格シリーズ運用要求仕様書

## 1. 文書情報
### 1.1 目的
YouTube 自動生成ワークフローを用いて資格シリーズを運用するための手順と要件を体系的に示す。読者はこの文書のみで宅建・日商簿記2級・応用情報技術者試験向けコンテンツを再現できる。

### 1.2 適用範囲
- Season `finance_news` と Season `qualification_prep`（内訳: `takken`, `boki2`, `ap`）に適用する。
- 設定ファイル、運用手順、品質管理を対象とする。

### 1.3 関連ファイル
| 種別 | パス | 用途 |
| --- | --- | --- |
| シリーズ設定 | `config/default.yaml` | Season 共通設定および Season 切替の中枢 |
| Season パック | `config/packs/<season>.yaml` | Season→Arc→Episode 定義 |
| プロンプト | `config/prompts.yaml` | Season 別プロンプトテンプレート |
| 運用記録 | `docs/releases/<season>/` | カレンダー、レビュー記録、ポストモーテム |
| 生成成果物 | `runs/<run_id>/season=<season>/arc=<arc>/episode=<episode>/` | スクリプト・音声・字幕・動画・メタデータ |

### 1.4 ディレクトリ構成
| パス | 役割 | 変更ルール |
| --- | --- | --- |
| `config/` | 設定・テンプレ資産の唯一の書き換えポイント。`config/default.yaml` を更新するだけで挙動を切り替え、他ディレクトリに設定を重複させない。 | Season/Arc/Episode の有効・無効、LLM/音声/字幕/映像テンプレ選択は全て本ディレクトリで完結させる。 |
| `src/` | CLI (`src/main.py`)、ワークフロー (`src/workflow.py`)、Step 群 (`src/steps/*`)、Provider 群 (`src/providers/*`)、モデル (`src/models.py`)、ユーティリティ (`src/utils/*`) を最小構成で保持。 | 新規処理は既存 Step/Provider のみ追加可とし、設定値参照は必ず `config/default.yaml` 経由に統一する。 |
| `docs/` | 運用仕様と各 Season の記録。`docs/markets/qualification.md` が資格シリーズ全体の単一ソース。 | 新規ブレーンストーミング資料は一時的であっても `docs/` 直下に集約し、同内容を他媒体へ複製しない。 |
| `runs/` | 実行結果の単一ストア。`runs/latest_stable/` で QA 済み Run を指す。 | 生成物の再利用・差し替えは最新 Run へのシンボリック参照で行い、手動コピーを禁止。 |
| `tests/` | `unit` `integration` `e2e` `fixtures` の 4 階層に限定。ステップ境界に合わせたテストのみ追加し、重複ケースを作らない。 | 追加テストは既存ディレクトリを再利用し、新たな階層や命名規則を持ち込まない。 |
| `assets/series/<season>/` | Season 固有の背景・ロゴ・配色定義。 | 配色や素材差し替えは Season Manager が `config/default.yaml` の参照キーのみ更新し、ファイルパスのハードコーディングを避ける。 |
| `scripts/` | 起動シーケンス (`start_aim.sh` など) と運用 CLI。 | 新スクリプトは既存起動順へ組み込み、冗長なラッパーを追加しない。 |

Season/Arc/Episode の切替、Step 有効化、Provider 選択は `config/default.yaml` の単一点で制御する。`src/` では設定値を読み取って実行するのみとし、定数・分岐・ディレクトリ構成を複製しないことで DRY と最小コードベースを維持する。

## 2. システム概要
### 2.1 ワークフロー
CLI `uv run python -m src.main` → `apps/youtube/cli.py` → `WorkflowOrchestrator` → 各 Step（`news` → `script` → `audio` → `subtitle` → `video` → `metadata`）。Season 設定に応じて各 Step の挙動が決まる。

### 2.2 Season 階層
| 階層 | 説明 | 例 |
| --- | --- | --- |
| Season | シリーズ全体の単位 | `finance_news`, `takken`, `boki2`, `ap` |
| Arc | Season 内のテーマ単位。試験分野や特集回を表現 | 宅建 `gyomu`（宅建業法） |
| Episode | Arc 内の個別コンテンツ。1 本 60〜120 秒 | `takken-gyomu-01` |

### 2.3 役割分担
| 役割 | 主担当 | 主な責務 |
| --- | --- | --- |
| Season Manager | 各 Season の責任者 | Season 設定更新、Pull Request 管理、法改正の反映 |
| Automation Operator | 自動化担当 | スケジューラ設定、実行ログ監視、障害一次対応 |
| QA Reviewer | 品質保証担当 | 生成物の事後検証、公開承認、LMS 連携確認 |

## 3. 用語定義
| 用語 | 定義 |
| --- | --- |
| Season | 動画シリーズ全体。金融シリーズや資格シリーズを識別する。 |
| Arc | 学習テーマのまとまり。Season 配信計画の最小単位。 |
| Episode | Arc を構成する 1 本の動画。導入→シナリオ→設問→解説→次回予告の構成を持つ。 |
| パックファイル | Season 固有の情報を保持する YAML ファイル。Arc と Episode を定義する。併せて `config/terms/<season>.yaml` を参照し、読み辞書・NGワード・表記ゆれ正規化を提供する。 |
| メタデータテンプレート | タイトル・説明・タグ・免責文を生成するフォーマット。Season 別に保持する。 |

## 4. Season 設定要件
### 4.1 `config/default.yaml`
`series` ノードに Season ごとの必須項目を定義する。

| キー | 必須 | 説明 | 例 |
| --- | --- | --- | --- |
| `id` | ○ | Season 識別子 | `takken` |
| `pack_path` | ○ | Season パックへのパス | `config/packs/takken.yaml` |
| `default_arc_order` | ○ | Arc 配信順の配列 | `["gyomu","hourei","rights","tax","flash_update"]` |
| `video_template` | ○ | 解像度・エフェクト等のプリセット名 | `vertical_exam_default` |
| `speaker_profiles` | ○ | 話者の名前・TTS 設定 | `lecturer`, `candidate`, `mentor` |
| `metadata_template` | ○ | 出力タイトル・説明・タグ | `takken_default` |
| `forbidden_terms` | ○ | Season 固有の禁止語リスト | `["闇","暴落"]` |
| `subtitle_mode` | ○ | 字幕モード | `jp_dual` |
| `fallback_llm_model` | ○ | 障害時に利用するモデル ID | `gemini/gemini-2.5-flash-preview-09-2025` |

### 4.2 Season パック (`config/packs/<season>.yaml`)
| 項目 | 階層 | 必須 | 内容 |
| --- | --- | --- | --- |
| `season.id` | Season | ○ | Season 識別子 |
| `season.name` | Season | ○ | Season 名称（例: 宅地建物取引士） |
| `season.exam_dates` | Season | ○ | 試験日一覧（ISO 8601） |
| `arcs[].id` | Arc | ○ | Arc 識別子 |
| `arcs[].name` | Arc | ○ | Arc 名称 |
| `arcs[].coverage` | Arc | ○ | 出題比率や学習比重（割合またはポイント） |
| `arcs[].release_plan` | Arc | ○ | 配信開始日・配信頻度 |
| `episodes[].episode_id` | Episode | ○ | 一意の Episode ID |
| `episodes[].template` | Episode | ○ | 使用するプロンプトテンプレート ID |
| `episodes[].source_refs` | Episode | ○ | 過去問番号・条文番号・公式記号 |
| `episodes[].difficulty` | Episode | ○ | 難易度ランク（例: `basic`, `advanced`） |
| `episodes[].duration_target` | Episode | ○ | 目標秒数 |
| `episodes[].cta_text` | Episode | ○ | 次の行動喚起文 |

### 4.3 プロンプトテンプレート (`config/prompts.yaml`)
- シーン順序を `intro`, `scenario`, `question`, `solution`, `teaser` として明記する。
- Season ごとに語調、参照データ挿入位置、学習者の想定レベルを記述する。
- 計算手順や条文を引用する場合は `{{ reference.<key> }}` 形式で埋め込み先を指定する。

## 5. 生成プロセス
### 5.1 実行ステップ
1. CLI 起動: `uv run python -m src.main --series <season> [--arc <arc>]`
2. 設定ロード: Season 設定とパックファイルを読み込み、Arc と Episode を決定。
3. Step 実行:  
   - `script`: プロンプトテンプレートと参照テーブルを用いて台本を生成。  
   - `audio`: 話者設定に基づき音声合成。  
   - `subtitle`: 字幕生成、必要なら二重字幕化。  
   - `video`: Season ごとのテンプレートで動画を生成。  
   - `metadata`: YouTube と LMS 用メタデータを出力。
4. 成果物保存: `runs/<run_id>/season=<season>/arc=<arc>/episode=<episode>/` に保存。

### 5.2 生成物仕様
| ファイル | 形式 | 主な内容 |
| --- | --- | --- |
| `script.json` | JSON | シーン区分、台本本文、正答、参照 ID |
| `audio.wav` | WAV 24kHz | 講師・受験生・メンターの対話音声 |
| `subtitles.srt` | SRT | 日本語字幕。Season 設定に応じて補助トラックを追加 |
| `video.mp4` | H.264 | Season テンプレートに基づく 60〜120 秒動画 |
| `metadata.json` | JSON | タイトル、説明、タグ、免責文、学習時間、復習推奨日、LMS 連携データ |
| `sync_report.json` | JSON | シーンごとの音声・映像・字幕タイムスタンプ差分（100 ミリ秒単位で記録） |

## 6. Season 別詳細仕様
### 6.2 `takken`
- Arc: `gyomu`, `hourei`, `rights`, `tax`, `flash_update`。
- Episode パターン: 条文引用→典型質問→ひっかけ事例→正解理由→次回予告。
- 映像: 1080×1920、宅地建物取引業者のオフィス背景、重要事項説明書をオーバーレイ。
- メタデータ: タイトルに「宅建 2025」「問番号」などを含め、免責文で判例の更新可能性を明記。

### 6.3 `boki2`
- Arc: `commercial`, `industrial`, `comprehensive`, `exam_flash`。
- Episode パターン: 仕訳提示→考え方→計算手順→答え→復習課題。
- 映像: 1080×1920、ホワイトボード風背景に仕訳テロップを重ねる。
- メタデータ: CBS 試験日（6 月・11 月）とネット試験常設を区別し、免責文で公式テキスト参照先を示す。

### 6.4 `ap`
- Arc: 午前 (`am_tech`, `am_management`, `am_strategy`)、午後 (`pm_security`, `pm_network`, `pm_database` など)、`flash_update`。
- Episode パターン: 簡易設問→思考ステップ→キーワード→答案骨子→次の演習案。
- 映像: 1080×1920、システム構成図やネットワークトポロジのオーバーレイ。
- メタデータ: シラバスバージョン（例: Ver.5.4）と設問カテゴリを明記。

## 7. 運用プロセス
### 7.1 フロー
1. **設定更新**: Season Manager がパックファイルと `series` 設定を編集し、Pull Request を提出。
2. **事前検証**: `scripts/validate_series.py` を実行し、スキーマ、アセット、試験日、トークン数に加えて `source_refs` の参照解決や `default_arc_order` に未定義 Arc がないかを確認。
3. **生成実行**: スケジューラまたは手動で CLI を起動し、Arc 単位に生成。
6. **記録**: `docs/releases/<season>/<YYYYMMDD>.md` に進捗と承認状況を記録。

### 7.2 スケジュール例
| Season | 実行タイミング | CLI 例 |
| --- | --- | --- |
| `takken` | 月 08:00 | `uv run python -m src.main --series takken --arc gyomu` など |
| `boki2` | 火 08:00 | `uv run python -m src.main --series boki2 --arc commercial` |
| `ap` | 土 10:00 | `uv run python -m src.main --series ap --arc am_tech` |

### 7.3 レビュー基準
- `script.json` の参照値と出力が一致している。

## 8. 品質管理
- 自動検証の結果は `runs/<run_id>/validation.json` に保存し、レビュー履歴と紐付ける。
- 免責文、法令改定、公式の改訂点は `docs/releases/<season>/ops.md` に随時追記する。

## 9. 自動化要件
- シラバス監視（設計想定）: `scripts/syllabus_watcher.py` が日次で公式 PDF・RSS を確認し、差分検知時に Issue を自動作成。
- Arc 配信カレンダー: `docs/releases/<season>/calendar.md` を生成し、試験日から逆算した配信タイミングを可視化。

## 11. LLM固有リスク
| リスク | 影響 | 対策 |
| --- | --- | --- |
| 時系列混在（改訂前後データの混同） | 古い情報の再公開 | パックファイルに改訂年月日を保持し、プロンプトで最新バージョンのみ許可。検証で改訂タグを照合。 |

## 12. 音声（TTS）・話者分離
| 項目 | 要件 |
| --- | --- |
| 話者ロール | Season 設定の `speaker_profiles` に講師・受験生・メンターを定義し、Episode ごとに役割を固定する。 |
| 音質 | 24kHz、ノイズなし、話者ごとの音量差 ±3dB 以内。`audio` Step で自動ノーマライズ。 |
| 分離検証 | `sync_report.json` に話者シーン別のタイムスタンプを記録し、台本ロールと一致するかを検証。 |
| ブリージング管理 | 話者交替時に 0.3 秒以上の無音（breathing space）を挿入し、クロスフェードを行わない。例: Instructor→Candidate 切替で 0.2 秒クロスフェードが発生した場合は無効化し字幕競合を防ぐ。 |
| アクセント辞書 | 法律・会計・IT の固有名詞（例: 担保権、圧縮記帳、RAID）を Season 別辞書に登録し、TTS 生成前に読みを統一する。 |

## 13. 字幕・二重字幕・組版
| 項目 | 要件 |
| --- | --- |
| 行幅制御 | `steps.subtitle.width_per_char_pixels` と `line_break_rules` を Season 設定に保持。漢字＋ラテン文字混在時でも 1 行 16〜40 文字相当で収まり、禁則処理（句読点行頭禁止、ローマ字途中改行禁止）を適用する。 |
| 禁止事項 | 全角スペースによる調整、句読点行頭、意味のない改行を禁止。 |
| 表記正規化 | `config/terms/<season>.yaml` の `normalize` ルールを字幕生成前に適用し、漢字・カナ・英数字のゆれを統一。 |
| 組版検証 | `sync_report.json` に字幕開始・終了タイムスタンプを記録し、音声とのズレを確認。二重字幕の改行位置も同時チェック。 |
| 数式・仕訳組版 | `boki2` Season では等幅フォントと桁揃えを使い、仕訳や表形式は字幕ではなく `video` Step のオーバーレイレイヤーに配置する。字幕側には要約のみ記載。 |

## 14. 映像合成・テンプレ
| 項目 | 要件 |
| --- | --- |
| 背景素材 | `assets/series/<season>/<arc>/background.png` を利用し、資格ごとにカラーコードとロゴを統一する。 |
| テンプレ管理 | テンプレ更新時は Season Manager がライセンスと変更点を `docs/releases/<season>/ops.md` に記録する。 |

## 15. メタデータ／YouTube運用
| 項目 | 要件 |
| --- | --- |
| タイトル | Season ごとの `metadata_template` を使用し、100 文字以内。`#Shorts` はアルゴリズム変動を踏まえてオン／オフ切替可能とし、付与時も資格名・Arc 名・試験日コードが冒頭に来るよう設計する。 |
| 説明文 | 冒頭 140 文字以内に KPI 語（例: 合格率アップ）を配置し、その後に学習目標、出題番号、参照資料リンク、免責文を記載。禁止語と誇張表現は Season のリストで検証する。 |
| タグ | Season ID、Arc ID、難易度、試験日コード、LMS 用キーワードを YAML で定義し、自動付与。`#Shorts` を除外した場合は YouTube 側の Shorts 判定をサムネ縦横比で担保する。 |
| 免責文 | 「資格団体非公式」「法令改訂の可能性」など Season 別テンプレを必須表示。 |
| プレイリスト | Season ごとに自動追加。Arc 単位でシリーズ順序を維持する。 |
| 公開設定 | 生成直後は限定公開。QA 承認後に公開に切り替え、LMS へ URL を連携。 |
| 投稿スケジュール | 試験カレンダーに従い、YouTube Studio API を用いて予約投稿。 |

## 16. スケジューリング／オーケストレーション
| 項目 | 要件 |
| --- | --- |
| 失敗時対応 | Step 失敗で停止した場合は `runs/<run_id>/state.json` を参照し、`uv run python -m src.main --resume <run_id>` で再開する。再生成時は `runs/latest_stable/<season>/<arc>.json` に最新安定版のポインタを更新し、旧 Run はアーカイブ扱いにする。 |
| スロットリング | Gemini API は 1 分間 4 リクエスト以内、Voicevox キューは同時 2 ジョブまで。`scheduler.yaml` にレート制限と指数バックオフ（待機: 30 秒→60 秒→120 秒）を明記し、TTS 課金のリトライ増大を防ぐ。 |
| 通知 | 実行完了・失敗を Slack/Discord に Webhook 通知。失敗時は Season Manager をメンション。 |
| 監査ログ | ジョブ実行履歴を `docs/releases/<season>/scheduler_log.md` に週次で追記し、SLA 達成率を記録。 |

## 23. アクセシビリティ
| 項目 | 要件 |
| --- | --- |
| 色設計 | サムネ・テロップはコントラスト比 4.5:1 以上を `scripts/validate_series.py` でチェックし、簿記の赤字・黒字など色依存情報はアイコンやハッチングで補足。 |
| 文字サイズ | 字幕フォントサイズは Season ごとの最低値（例: 72pt）を維持し、縦型でも可読性を確保。 |

## 28. 成果物一覧
| 成果物 | 目的 |
| --- | --- |
| Season 分離済み `config/default.yaml` | Season 切替と共通設定の管理 |
| `config/packs/<season>.yaml` | Season→Arc→Episode の唯一の参照元 |
| `config/prompts.yaml` Season テンプレート | シーン構成と参照テーブル挿入位置の定義 |
| `docs/releases/<season>/ops.md` | 運用手順と週次メモ |
| `docs/releases/<season>/calendar.md` | 配信スケジュールの可視化 |
