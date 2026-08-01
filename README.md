# 2511youtuber — 金融ニュース動画生成パイプライン

ニュース候補、台本、VOICEVOX音声、字幕、FFmpeg動画、サムネイル、メタデータを工程別に生成するワークフローです。

## 最重要：外部公開は二重承認制

監査時点の`config/default.yaml`には、YouTubeが`enabled: true`、`dry_run: false`、`default_visibility: public`、自動運用が`enabled: true`という危険な既定値が残っています。

実際の送信点`src/providers/youtube.py`へ安全ゲートを追加し、設定ファイルだけでは外部投稿できないようにしました。

### 通常の確認実行

`dry_run: true`で実行します。外部副作用は発生せず、結果に次を保存します。

```json
{
  "status": "dry_run",
  "external_side_effect": false,
  "video_id": "dry_..."
}
```

### private / unlistedで実投稿する場合

動画、メタデータ、出典、権利を人間が確認したプロセスだけで、次を設定します。

```bash
export YOUTUBE_EXTERNAL_PUBLISH_APPROVED="I_UNDERSTAND_THIS_UPLOADS_EXTERNALLY"
```

### publicで公開する場合

外部投稿承認に加えて、公開承認を別に要求します。

```bash
export YOUTUBE_PUBLIC_VISIBILITY_APPROVED="I_UNDERSTAND_THIS_WILL_BE_PUBLIC"
```

片方でも欠けると`PublicationGateError`で停止します。公開承認は環境へ常設せず、確認済みの単一実行だけへ付与してください。

## 監査で修正したYouTube処理

- `dry_run=false`だけでOAuthと投稿へ進む挙動を禁止
- public投稿に別の明示承認を追加
- メタデータ側でvisibilityをpublicへ上書きしても公開ゲートを再検査
- 空動画、空タイトル、空説明文を拒否
- 投稿API応答にvideo IDがない場合を成功扱いしない
- dry-run結果へ`external_side_effect: false`を追加
- 実投稿結果へ`external_side_effect: true`を追加
- 認証キャッシュを危険な`pickle`からGoogle認証JSONへ変更
- トークンファイルの権限を可能な環境では`0600`へ制限
- OAuth scopeを`youtube.upload`へ縮小
- UTC投稿時刻を保存
- 公開ゲートの回帰テストを追加

## 設定上の未解決事項

`config/default.yaml`には`steps.news`キーが重複しています。現在は後側のマッピングがPyYAMLで採用されますが、重複キーを許容すること自体が設定監査上の問題です。次の設定整理では、重複キーを削除し、YAMLローダーへ重複キー拒否を追加する必要があります。

また、既定設定そのものも次へ変更すべきです。

```yaml
steps:
  youtube:
    enabled: false
    dry_run: true
    default_visibility: private
automation:
  enabled: false
```

現時点では、実送信点の二重承認ゲートが最終防壁です。

## 基本フロー

```text
ニュース候補取得
  → 出典・発生日・公開日・重複を監査
  → 台本生成
  → 人間または検証器による数値・引用・固有名詞確認
  → 音声・字幕・映像・サムネイル生成
  → private/dry-runで確認
  → 明示承認がある実行だけ外部投稿
```

## 実行

```bash
uv sync
cp config/.env.example config/.env

task run
task test:fast
task test:all
```

「テスト合格」は、外部ニュースの正しさ、投資内容の妥当性、著作権、YouTube公開品質を保証しません。

## YouTubeゲートのテスト

```bash
python -m unittest tests.unit.test_youtube_publication_gate -v
```

確認項目:

- 承認なしの非dry-runを拒否
- publicに別承認が必要
- dry-runに外部副作用がない
- 空動画を拒否
- 空タイトル・空説明文を拒否

## 権利と事実確認

- ニュース本文、画像、立ち絵、音声、BGM、フォント、動画素材の利用条件を個別確認する
- 株価・決算・経済統計へ基準日と単位を付ける
- LLMの生成文を一次情報として扱わない
- 投資助言・利益保証・煽動的表現を避ける
- チェックポイント再利用時はニュースのas-ofと入力ハッシュを確認する

このリポジトリは自動公開装置ではなく、確認可能な動画成果物を作る制作パイプラインとして運用します。

**README最終監査:** 2026-08-02
