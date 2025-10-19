# 動画生成・素材収集手法の比較

## 概要

youtube-ai-v2プロジェクトにおける動画素材の収集と生成に関する手法をまとめる。
現在の実装はストックフォトAPI（Pixabay/Pexels）を利用しているが、AI動画生成サービスの利用も検討する。

## 現在の実装: ストックフォトAPI

### Pexels API

**料金:** 完全無料

**レート制限:**
- デフォルト: 分あたりの上限あり（具体的な数値は非公開）
- Pexelsへの適切なクレジット表記を提供できれば上限を解除可能
- 月間150億リクエスト以上を処理（全体）

**利用条件:**
- 無料
- クレジット表記不要
- ライセンス費用なし

**実装:**
- `app/services/media/stock_footage_manager.py`: ダウンロード・24時間キャッシュ
- `app/services/media/visual_matcher.py`: スクリプトキーワードとのマッチング

**API仕様:**
- エンドポイント: `https://api.pexels.com/videos/search`
- 認証: APIキー（ヘッダー）
- クエリパラメータ: `query`, `per_page`, `orientation`, `size`
- レスポンス: JSON（動画URL、サムネイル、メタデータ）

### Pixabay API

**料金:** 完全無料

**レート制限:**
- デフォルト: 100リクエスト/分
- キャッシュ必須: 24時間
- 永続的なホットリンク禁止（サーバーにダウンロード必須）

**利用条件:**
- 無料
- Pixabayへの言及必須
- ホットリンク禁止

**API仕様:**
- エンドポイント: `https://pixabay.com/api/videos/`
- 認証: APIキー（クエリパラメータ）
- クエリパラメータ: `key`, `q`, `per_page`, `video_type`
- レスポンス: JSON

### Shutterstock API（参考）

**料金:** 有料プラン

**レート制限:**
- 無料アカウント: 100リクエスト/時
- APIリクエストが上限を超えると429エラー
- ヘッダー: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`

**プラン:**
- 無料: 500アセット/月、100レスポンス制限、限定メディアライブラリ
- 有料: 1億画像、400万動画、10万音楽トラック（Unlimited Choice）

**動画素材単価:**
- サブスクリプション: $8.32-$9.95/クリップ
- オンデマンド: $49-$194/クリップ（SD/HD/4K）

**実装ステータス:** 未実装（高コスト）

---

## AI動画生成サービス

### 1. Google Vertex AI - Veo 3/3.1

**料金:**
- **$0.75/秒**（生成された動画・音声の秒数）
- 成功した生成のみ課金（失敗時は無料）

**レート制限:**
- プレビューモデルは安定版より厳しい制限
- Vertex AI → Quotasで確認・増加リクエスト可能

**出力仕様:**
- 解像度: 最大1080p（Veo 3.1）
- 長さ: 最大20秒（予想）
- フォーマット: MP4（推定）

**精度:**
- 最新のVeo 3.1はテキスト→動画の精度が高い
- 物理法則の理解、モーション品質で高評価

**API設定:**
- プラットフォーム: Google Cloud Vertex AI
- 認証: サービスアカウントJSONキー（`GOOGLE_APPLICATION_CREDENTIALS`）
- エンドポイント: Vertex AI Veo API
- リージョン: `us-central1`など

**実装時の注意:**
- Gemini API（Google AI Studio）と混同しない
- Vertex AI専用のクライアントライブラリ使用
- 環境変数: `GOOGLE_APPLICATION_CREDENTIALS`

**コスト試算（60秒動画）:**
- 60秒 × $0.75 = **$45/動画**
- 非現実的に高い（ストックフォト無料と比較）

### 2. OpenAI Sora 2

**API可用性:** **2025年10月時点で未公開**
- 発表: "API coming soon"（具体的な日付なし）
- 現在はChatGPT Plus/Pro経由のみ

**料金（API予想）:**
- Standard 720p: **$0.10/秒**（12秒で$1.20）
- Pro 1080p: **$0.50/秒**（12秒で$6.00）
- 推定範囲: $0.50-$3.00/動画

**サブスクリプション（現行）:**
- ChatGPT Plus: 50優先動画/月（1000クレジット）、720p、5秒まで
- ChatGPT Pro: 500優先動画/月（10000クレジット）+ 無制限relaxed、1080p、20秒まで

**レート制限:**
- RPM（Requests Per Minute）による制限
- Proティアほど厳しい制限の可能性

**出力仕様:**
- 解像度: 最大1080p
- 長さ: 最大20秒
- 透かし: アプリ版は透かしあり、API版は透かしなし（予想）

**精度:**
- テキスト→動画の高精度
- 物理シミュレーション、複雑なカメラワークに対応

**API設定（公開後の予想）:**
- エンドポイント: `https://api.openai.com/v1/sora/generate`（仮）
- 認証: Bearer token（`OPENAI_API_KEY`）
- リクエスト: JSON（prompt, duration, resolution）

**実装時の注意:**
- API公開待ち（2025年後半？）
- 価格変動の可能性
- 米国・カナダ限定の可能性

**コスト試算（60秒動画、Pro 1080p）:**
- 60秒 × $0.50 = **$30/動画**
- 依然として高コスト

### 3. Runway Gen-3 Alpha Turbo

**料金:**
- クレジット購入: **$0.01/クレジット**
- Gen-3 Alpha Turbo: **5クレジット/秒 = $0.05/秒**
- 10秒動画 = 50クレジット = **$0.50**

**レート制限:**
- ティアベースの同時実行制限（concurrency limit）
- RPMの上限なし（日次上限内であれば）
- 上限を超えるとキューイング（自動待機）

**ティア制限例:**
- Tier 3: Gen-4 Turbo 5同時実行、Aleph 5同時実行、Act-Two 5同時実行
- カスタムティア・エンタープライズ契約で上限増加可能

**出力仕様:**
- 解像度: 最大1080p（Gen-3）
- 長さ: 最大10秒（デフォルト）
- フォーマット: MP4

**精度:**
- Gen-3は高速・低コスト重視
- Gen-4（より高精度）も利用可能（別料金）

**API設定:**
- エンドポイント: `https://api.dev.runwayml.com/v1/generations`
- 認証: APIキー（ヘッダー）
- リクエスト: JSON（prompt, model, duration）
- Webhook対応（生成完了通知）

**実装手順:**
1. Developer Portalでアカウント作成
2. APIキー取得
3. クレジット購入（$0.01/credit）
4. POST `/v1/generations`でリクエスト
5. ステータス確認または Webhook受信

**コスト試算（60秒動画）:**
- 60秒 × $0.05 = **$3.00/動画**
- まだ高いが他より現実的

### 4. Luma Dream Machine

**料金（API経由）:**
- 公式API: 現在は第三者プロバイダー経由
- **PiAPI: $0.20/動画**（Luma Dream Machine 2）
- 100動画 = $20
- fal.ai: $0.50/動画（比較用）

**Webプラットフォーム:**
- Lite: $9.99/月、3200クレジット/月（非商用、透かしあり）
- Plus: $29.99/月、10000クレジット/月（商用可、透かしなし）
- Unlimited: $94.99/月、10000高速 + 無制限relaxed

**クレジット消費:**
- 5秒動画: 170クレジット
- 10秒動画: 340クレジット

**出力仕様:**
- 解像度: 1080p
- 長さ: 最大10秒（標準）
- フォーマット: MP4

**精度:**
- Dream Machine 2（2025）は高精度
- 動きの滑らかさ、物体の一貫性で評価高い

**API設定（PiAPI経由）:**
- エンドポイント: `https://api.piapi.ai/luma/generate`
- 認証: PiAPI APIキー
- リクエスト: JSON（prompt, duration）

**実装時の注意:**
- 公式APIは未公開（第三者プロバイダー利用）
- PiAPIの信頼性・利用規約確認必須

**コスト試算（60秒動画）:**
- 60秒 ÷ 10秒 = 6リクエスト
- 6 × $0.20 = **$1.20/動画**
- 最も低コスト

---

## 比較表

| サービス | 料金/秒 | 60秒動画コスト | レート制限 | 精度 | API可用性 | 実装難易度 |
|---------|---------|---------------|-----------|------|----------|----------|
| **Pexels API** | **無料** | **無料** | 分あたり上限（解除可） | ストック映像 | 公開 | 低（実装済） |
| **Pixabay API** | **無料** | **無料** | 100/分 | ストック映像 | 公開 | 低（実装済） |
| Shutterstock | $8.32/クリップ | 不定 | 100/時（無料） | 高品質ストック | 公開 | 中 |
| **Veo 3.1** | $0.75 | **$45** | Quota制 | 最高 | 公開 | 中 |
| **Sora 2** | $0.10-$0.50 | **$6-$30** | RPM制 | 最高 | **未公開** | 不明 |
| **Runway Gen-3** | $0.05 | **$3** | Tier制 | 高 | 公開 | 中 |
| **Luma DM** | $0.02 | **$1.20** | 不明 | 高 | 第三者のみ | 中 |

---

## 過去の実装試行

### 失敗事例: `../`での動画素材収集

**背景:**
- プロジェクトルート外のディレクトリで実装試行
- ストックフォトAPIの統合テスト

**失敗原因:**
- パス管理の複雑化
- 設定ファイルの参照エラー
- キャッシュディレクトリの権限問題

**教訓:**
- プロジェクトルート内で実装すること
- `cache/`ディレクトリを活用
- `app/services/media/`に機能を集約

---

## 推奨実装戦略

### 短期（現行維持）

**継続使用: Pexels + Pixabay API**

**理由:**
- 完全無料
- 十分な動画素材ライブラリ
- 既に実装済み
- 安定稼働

**改善点:**
- キャッシュ戦略の最適化
- マッチング精度向上
- 複数APIの自動フォールバック

### 中期（選択的AI利用）

**Luma Dream Machine（PiAPI経由）**

**理由:**
- 最低コスト（$1.20/60秒動画）
- 高精度
- 即座に利用可能

**利用シーン:**
- ストックフォトに適切な素材がない場合
- カスタム映像が必要な場合（例: 特定の企業ロゴ、未来的なシーン）

**実装:**
```python
# app/services/media/ai_video_generator.py
import requests

class LumaDreamMachineProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.piapi.ai/luma/generate"

    def generate_video(self, prompt: str, duration: int = 10) -> str:
        """
        動画を生成してURLを返す

        Args:
            prompt: 動画生成プロンプト
            duration: 秒数（5または10）

        Returns:
            動画URL
        """
        response = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": prompt, "duration": duration}
        )
        response.raise_for_status()
        return response.json()["video_url"]
```

**設定:**
```yaml
# config/default.yaml
providers:
  video_generation:
    luma:
      enabled: false  # デフォルトは無効
      api_key_env: "LUMA_PIAPI_KEY"
      max_duration: 10
      fallback_to_stock: true
```

### 長期（監視対象）

**Sora 2 API公開待ち**

**理由:**
- OpenAIの信頼性
- 透かしなし
- 高精度

**監視項目:**
- API公開日
- 最終価格（$0.10/秒以下が理想）
- 利用可能地域
- レート制限

**Runway Gen-3の検討**

**理由:**
- 現在利用可能
- 中程度のコスト（$0.05/秒）
- 公式API

**評価項目:**
- ティア制限の実運用
- 日本語プロンプト対応
- 動画品質

---

## 実装チェックリスト

### ストックフォトAPI（実装済）

- [x] Pexels API統合
- [x] Pixabay API統合
- [x] 24時間キャッシュ
- [x] visual_matcher.pyでキーワードマッチング
- [x] broll_generator.pyでFFmpeg合成
- [ ] 複数APIの自動フォールバック
- [ ] キャッシュヒット率のロギング

### AI動画生成（未実装）

- [ ] Luma Dream Machine（PiAPI）統合
- [ ] 設定ファイルへの追加
- [ ] コスト追跡ロギング
- [ ] ストックフォトとのフォールバックチェーン
- [ ] 生成動画のキャッシュ（プロンプト→動画URL）
- [ ] Sora API公開の監視
- [ ] Runway Gen-3の評価テスト

---

## 定型短尺動画のプロンプト設計（Sora用）

### 概要

YouTube動画の**導入**、**幕間**、**終了後**に挿入する10秒以下の定型動画を生成するためのプロンプト設計。
ブランド認知とプロフェッショナルな印象を与え、視聴者の離脱を防ぐことが目的。

### 1. 導入動画（イントロ）- 春日部つむぎ 3パターン

**設計方針:**
- キャラクターの世界観を確立し、視聴者を自然にニュース本編へ導く
- 動き・視線・環境音で心理的な流れを作る（静→気づき→誘い）
- 完全ひらがなで発音の一貫性を確保
- 15秒で完結、再利用可能

---

#### パターンA: 「駅ホームの朝」

**意図:** 社会へ出ていく始まり、日常からニュースへの接続

**Soraプロンプト:**
```
Morning light spreads across a quiet train platform.
Tsumugi steps forward, adjusting her bag strap and looking at the horizon line where tracks converge.
「あさの　ひかりが　かわると、　せかいの　はなしも　すこし　かわりますね。」

She walks slowly along the yellow safety line, faint train sounds in the distance.
「きょうも　たくさんの　ひとが　うごいて、　すうじが　うまれています。」

She stops, opens her notebook, pages flutter gently in the wind.
「その　ひとつひとつに、　いみが　かくれているかも。」

She looks at the camera with a soft smile, closing the notebook.
「さあ、　きょうの　ニュースを　いっしょに　みていきましょう。」

Visual: soft anime lighting, mint-green accents, gentle depth of field, warm morning tone
Audio: faint platform ambience, light wind, breathing pauses every 3 seconds
Camera: slow dolly-in from side angle, steady framing
Duration: 15 seconds, 1080p
```

**コスト:** 15秒 × $0.50 = **$7.50**（初回のみ、以降再利用で$0）

---

#### パターンB: 「屋上の朝」

**意図:** 視点をひらく静かな覚醒、上を向くことで希望と知性を表現

**Soraプロンプト:**
```
Morning light spreads across a city rooftop.
A light breeze moves a line of laundry beside the railings.
Tsumugi steps into the sunlight, closing the door behind her.
She takes a quiet breath and looks up at the sky.
「ひかりが　すこし　かわりましたね。きょうの　そらは　やさしいいろです。」

She walks slowly to the edge, placing her hands on the cool metal rail.
Cars move far below, faint and distant.
「ひとも　まちも、　いつも　うごいています。すうじも　その　こえの　ひとつです。」

The wind rises, brushing through her hair. She opens her notebook and the pages flutter.
「でも　きょうの　いみを　つくるのは、　いまを　みている　わたしたちです。」

She closes the notebook gently and smiles at the horizon.
「さあ、　あたらしいいちにちを　いっしょに　はじめましょう。」

Visual: rooftop morning, soft anime lighting, blue sky gradient, distant cityscape
Audio: wind, faint traffic below, bird calls, natural breathing pauses
Camera: slow walk-in from door to rail, gentle parallax
Duration: 15 seconds, 1080p
```

**コスト:** 15秒 × $0.50 = **$7.50**（初回のみ）

---

#### パターンC: 「夜の図書室」

**意図:** 内なる静けさと知性、灯りで語る構成、落ち着きと惹きつけのバランス

**Soraプロンプト:**
```
A quiet library after sunset.
Soft desk light spills across the wooden table.
Tsumugi turns a page, pauses, and looks toward the window where the city lights flicker beyond the glass.
「よるの　まちって、　ちょっと　ほっとしますね。」

She sets down her pen and leans her cheek on her hand.
Her eyes follow the slow movement of a clock's second hand.
「きょうも　たくさんの　できごとが　すぎていきました。すうじも　その　きおくの　ひとつです。」

She closes the book softly. Dust motes float in the warm light.
「でも　そのなかに、　あしたを　つくる　ヒントが　かくれているのかも。」

She looks at the camera and smiles faintly, the desk light glowing behind her.
「いっしょに　みつけに　いきましょう。　きょうのニュースです。」

Visual: warm desk lamp glow, dark library shelves, soft bokeh, dust particles
Audio: quiet ambience, faint clock tick, page turn, gentle breathing pauses
Camera: static then slow push-in on tsumugi's face
Duration: 15 seconds, 1080p
```

**コスト:** 15秒 × $0.50 = **$7.50**（初回のみ）

---

**技術仕様（共通）:**
- 時間: 15秒
- 解像度: 1080p
- スタイル: アニメ風、柔らかい照明、ミント/青/金色のアクセント
- 音声: 環境音のみ（BGMは後処理で追加）
- セリフ: 完全ひらがな（Voicevox音声合成で自然な発音）

**運用戦略:**
- 3パターンをローテーション（飽き防止）
- 朝配信→A/B、夜配信→C など時間帯で使い分け
- 初回合計コスト: $7.50 × 3 = **$22.50**
- 100動画での追加コスト: $0.225/動画

**実装:**
- `config/default.yaml`の`steps.video.intro_outro.intro_paths`に3パターンのパスを配列で設定
- `src/steps/video.py`でランダムまたは時刻ベースで選択

### 2. 幕間動画（トランジション）

**意図:**
- 話題の切り替わりを視覚的に示す
- 視聴者に短い休憩を与える
- 離脱率を下げる（視覚的刺激で飽きさせない）

**場面:**
- 異なるニューストピック間（例: FOMCニュース → 日銀政策の切り替え）
- 長い動画（10分以上）の中盤

**プロンプト:**
```
A 3-second transition sequence: abstract geometric shapes (cubes, hexagons) in metallic silver and deep blue colors rotate smoothly in 3D space against a dark gradient background. Subtle motion blur creates a sense of speed. The shapes align into a grid formation, then dissolve into particles. Clean, modern, business-oriented design. 3 seconds. 1080p.
```

**日本語訳:**
3秒のトランジションシーケンス: メタリックシルバーと深い青色の抽象的な幾何学形状（立方体、六角形）が暗いグラデーション背景の3D空間で滑らかに回転。微妙なモーションブラーが速度感を演出。形状はグリッド状に整列し、その後粒子に分解。クリーン、モダン、ビジネス指向のデザイン。3秒。1080p。

**技術仕様:**
- 時間: 3秒
- 解像度: 1080p
- スタイル: 抽象的、ビジネスライク
- 音声: なし（トランジション音を別途追加）

**コスト（Sora Pro 1080p）:**
- 3秒 × $0.50 = **$1.50/動画**
- 2-3パターン生成して使い分け可能

### 3. 終了動画（アウトロ）- 春日部つむぎ 2パターン

**設計方針:**
- 視聴者に満足感と次回への期待を与える
- チャンネル登録・高評価の自然な誘導
- キャラクターの温かみで締めくくる

---

#### パターンA: 「教室の夕暮れ」

**意図:** 1日の終わり、学びの充実感、次への期待

**Soraプロンプト:**
```
Late afternoon in a quiet classroom.
Golden sunlight streams through the window, casting long shadows across desks.
Tsumugi closes her notebook, stretches gently, and looks toward the window.
「きょうの　ニュース、　どうでしたか？」

She walks to the window, traces her finger along the glass where light patterns shift.
「すうじの　むこうに　ひとが　いて、　ものがたりが　ある。　それを　かんじられたら　うれしいです。」

She turns back to the camera, soft smile, holding her notebook to her chest.
「また　あした、　あたらしい　はっけんを　いっしょに　さがしましょうね。」

Light fades to warm orange, gentle fade to dark with text placeholder in center.

Visual: warm afternoon light, soft anime aesthetic, mint-green bag on desk
Audio: quiet classroom ambience, faint clock tick, bird calls fading
Camera: static then slow dolly-in, gentle fade-out
Duration: 12 seconds, 1080p
```

**コスト:** 12秒 × $0.50 = **$6.00**（初回のみ）

---

#### パターンB: 「図書室の閉館」

**意図:** 静かな満足感、知識の余韻、また会いましょうの約束

**Soraプロンプト:**
```
A library at closing time, soft desk lamp glowing.
Tsumugi gathers her books and stacks them neatly, pausing to look at the spines.
「きょうも　いろんな　かずが　ありましたね。　でも　それは　ぜんぶ　ひとの　いとなみです。」

She stands, adjusts her cardigan, and walks toward the camera with books in hand.
「この　ちしきが、　あしたの　あなたの　せんたくを　すこしでも　てつだえたら。」

She stops at the doorway, looks back with a gentle smile, and turns off the desk lamp.
「それじゃ、　また　つぎの　ニュースで。　おつかれさまでした。」

Fade to dark blue with soft light rays, text placeholder appears.

Visual: warm lamp glow fading to darkness, library shelves silhouette
Audio: quiet footsteps, book sounds, light switch click, gentle breathing
Camera: follow tsumugi's walk, fade to black
Duration: 12 seconds, 1080p
```

**コスト:** 12秒 × $0.50 = **$6.00**（初回のみ）

---

**技術仕様（共通）:**
- 時間: 12秒
- 解像度: 1080p
- スタイル: アニメ風、夕暮れ/夜の温かい照明
- 音声: 環境音のみ（アウトロBGMは後処理で追加）
- セリフ: 完全ひらがな
- 後処理: テキストオーバーレイ（「チャンネル登録・高評価お願いします」「次回もお楽しみに」）

**運用戦略:**
- 朝配信→パターンA、夜配信→パターンB
- 初回合計コスト: $6.00 × 2 = **$12.00**
- 100動画での追加コスト: $0.12/動画

**実装:**
- `config/default.yaml`の`steps.video.intro_outro.outro_paths`に2パターンのパスを配列で設定
- FFmpegでテキストオーバーレイを追加（drawtext filter使用）

### プロンプト設計の原則（春日部つむぎイントロ/アウトロ向け）

1. **具体的な動作シーケンス:** "tsumugi closes notebook" → "walks to window" → "looks at camera" のように段階的に動きを指定
2. **環境の細部:** "sunlight filtering through hair", "pages flutter in wind" など小さな動きで臨場感を出す
3. **視線の流れ:** "gazes out window" → "turns to camera" → "soft smile" で視聴者を自然に巻き込む
4. **完全ひらがなセリフ:** Voicevox音声合成の発音安定性のため、漢字・カタカナを使わない
5. **心理的トーン:** "calm yet curious", "intelligent warmth" で感情の方向性を明示
6. **呼吸のタイミング:** "breathing pauses every 3 seconds" でリズムを作る
7. **カメラワーク:** "slow dolly-in", "gentle parallax", "static then push-in" で視覚的な変化を設計
8. **時間配分:** 15秒を3-4秒ずつに分割し、各セクションに明確な目的を持たせる
9. **音響設計:** "faint platform ambience", "light wind", "clock tick" で世界観を補強
10. **色彩と照明:** "mint-green accents", "warm morning tone", "soft bokeh" でキャラクター設定と統一

### 実装時の考慮事項

**再利用戦略:**
- イントロ3パターン + 幕間3パターン + アウトロ2パターン = 合計8動画クリップ
- ローテーション・時間帯・文脈で自動選択
- 初回生成後は全動画で再利用（追加コストなし）

**コスト最適化（Sora Pro 1080p）:**
- イントロ3本: $7.50 × 3 = **$22.50**
- 幕間3本: $1.50 × 3 = **$4.50**
- アウトロ2本: $6.00 × 2 = **$12.00**
- **合計初回投資: $39.00**
- 100動画での追加コスト: $0.39/動画（再利用）

**Luma Dream Machine代替（96%コスト削減）:**
- イントロ15秒（10秒×2リクエスト）: $0.20 × 2 × 3 = **$1.20**
- 幕間3秒（10秒→トリミング）: $0.20 × 3 = **$0.60**
- アウトロ12秒（10秒×2リクエスト）: $0.20 × 2 × 2 = **$0.80**
- **合計初回投資（Luma）: $2.60**
- Sora比96%削減、100動画での追加コスト: $0.026/動画

**推奨戦略:**
1. まずLumaで全8パターン生成（$2.60）
2. 品質確認後、必要なパターンのみSoraで再生成
3. 最高品質が必要な場合のみSora全面採用（$39.00）

**FFmpegでの合成:**
```python
# src/steps/video.py での実装例
import random
from datetime import datetime

def select_intro_clip(config: dict) -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return random.choice([
            config["intro_paths"]["station"],
            config["intro_paths"]["rooftop"]
        ])
    else:
        return config["intro_paths"]["library"]

def select_outro_clip(config: dict) -> str:
    hour = datetime.now().hour
    return config["outro_paths"]["classroom"] if hour < 18 else config["outro_paths"]["library"]

def add_intro_outro(intro: str, main: str, outro: str, output: str):
    ffmpeg.concat(
        ffmpeg.input(intro),
        ffmpeg.input(main),
        ffmpeg.input(outro),
        v=1, a=1
    ).output(output, vcodec='libx264', preset='medium', crf=23).run()
```

**設定ファイル:**
```yaml
# config/default.yaml
steps:
  video:
    intro_outro:
      enabled: true
      intro_paths:
        station: "assets/video/intro_station_15sec.mp4"
        rooftop: "assets/video/intro_rooftop_15sec.mp4"
        library: "assets/video/intro_library_15sec.mp4"
      transition_paths:
        - "assets/video/transition_geometric_3sec.mp4"
        - "assets/video/transition_v2_3sec.mp4"
        - "assets/video/transition_v3_3sec.mp4"
      outro_paths:
        classroom: "assets/video/outro_classroom_12sec.mp4"
        library: "assets/video/outro_library_12sec.mp4"
      outro_overlay:
        enabled: true
        text: "チャンネル登録・高評価お願いします\n次回もお楽しみに"
        font_path: "assets/fonts/ZenMaruGothic-Bold.ttf"
        font_size: 48
        color: "white"
        position: "center"
```

**Voicevox音声合成統合:**
```python
# イントロ/アウトロのセリフを事前に音声合成
from src.providers.tts import VoicevoxProvider

voicevox = VoicevoxProvider(speaker_id=8)  # 春日部つむぎ

intro_lines = [
    "あさの　ひかりが　かわると、　せかいの　はなしも　すこし　かわりますね。",
    "きょうも　たくさんの　ひとが　うごいて、　すうじが　うまれています。"
]

for i, line in enumerate(intro_lines):
    audio = voicevox.synthesize(line)
    audio.export(f"assets/audio/intro_line_{i}.wav", format="wav")
```

**音声とSora動画の統合:**
Soraで生成した動画（環境音のみ）に、Voicevoxで合成した音声をFFmpegでミックス。

```bash
ffmpeg -i intro_station_visual.mp4 -i intro_station_audio.wav \
  -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 \
  intro_station_15sec.mp4
```

---

## 参考リンク

- [Pexels API Documentation](https://www.pexels.com/api/documentation/)
- [Pixabay API Documentation](https://pixabay.com/api/docs/)
- [Vertex AI Veo Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- [Runway API Documentation](https://docs.dev.runwayml.com/)
- [Luma Dream Machine](https://lumalabs.ai/dream-machine)
- [PiAPI Luma Documentation](https://piapi.ai/dream-machine-api)

---

## 更新履歴

- 2025-10-19: 初版作成（Pexels/Pixabay実装状況、Veo/Sora/Runway/Luma調査結果）
- 2025-10-19: 定型短尺動画のプロンプト設計を全面刷新
  - イントロ3パターン（駅ホーム/屋上/図書室）15秒
  - アウトロ2パターン（教室/図書室）12秒
  - 春日部つむぎのキャラクター世界観を反映
  - 動作シーケンス・視線の流れ・完全ひらがなセリフで設計
  - Lumaでの代替案（96%コスト削減）と実装コード例を追加
