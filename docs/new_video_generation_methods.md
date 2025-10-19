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
