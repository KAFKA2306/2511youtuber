# 動画生成・素材収集手法の比較（youtube-ai-v2 / v3設計案）

**版:** 2025-10-19 初稿（全面刷新）
**対象:** 素材収集・AI動画生成の方式選定、コスト最適化、実装ガイド

---

## 0. エグゼクティブサマリー

* **短期**は既存の**Pexels/Pixabay**（無料）を主軸に継続。
  改善は「キャッシュ最適化」「複数API自動フォールバック」「一致率向上」の3点に集中。
* **中期**は不足素材のみ **Luma Dream Machine（PiAPI）** を**代替生成**で補完。
  10秒単価が低く、初期投資を抑えた**ハイブリッド構成**が最適。
* **長期**は **Sora API** 正式提供・価格確定を待ち、**高品質版だけ差し替え**。
  Runway Gen-3 は当面ベンチ比較用のセカンドオプション。
* **運用**は「リユース前提」。8本の汎用クリップ（イントロ3/幕間3/アウトロ2）を先に作り、ローテーションで使い回す。
* **KPI**は「1本あたり可変費」「視聴維持率（前後10秒）」「一致率」「生成失敗率」。
  いずれも**自動計測・日次集計**に統合。

---

## 1. 方式一覧（要点と立ち位置）

| 区分   | 手段              |          コスト/秒 | 強み         | 弱み        | 採用方針       |
| ---- | --------------- | -------------: | ---------- | --------- | ---------- |
| ストック | **Pexels**      |             無料 | 無料・実装済     | 表現の自由度が限定 | **主軸**（短期） |
| ストック | **Pixabay**     |             無料 | 無料・API仕様明確 | ホットリンク不可  | **主軸**（短期） |
| ストック | Shutterstock    |         クリップ課金 | 高品質        | 高コスト      | 参考（保留）     |
| 生成   | **Luma（PiAPI）** |     ≒$0.02/秒換算 | 低コスト・1080p | 公式APIでない  | **補完**（中期） |
| 生成   | Runway Gen-3    |       ≒$0.05/秒 | 公式API・高速   | 10秒標準     | 比較（検証）     |
| 生成   | **Sora**        | 仮≒$0.10–0.50/秒 | 最高品質       | 価格・API未確定 | **監視**（長期） |

> 生成系の価格は変動し得る前提。最新の実測を常時反映すること。

---

## 2. 現行（ストックAPI）を“強くする”三点

### 2.1 キャッシュ最適化

* 24hだけでなく**LRU + 指定TTL**の二段構え。
* ヒット率・回避保存（同一解像度・同一クリエイター）を記録し**再学習**に利用。

### 2.2 自動フォールバック

* Pexels → Pixabay →（在庫不足）→ 生成系 の**直列チェーン**。
* 失敗時は即時スキップし、次APIへ**遅延ゼロ**で移行。

### 2.3 一致率向上（visual_matcher）

* スクリプトの**名詞句・動詞句**を抽出し、**時間帯/天候/視線/距離**タグへ正規化。
* 例：`「まどぎわ」「やわらかいあさ」「かぜ」→ window, morning soft light, gentle wind, medium shot`

---

## 3. 生成系の使いどころ（ハイブリッド設計）

* **原則**：無料ストックで**80–90%**を賄い、不足分だけ**生成で補完**。
* **ケース**：

  1. 固有シーン（駅ホーム/屋上/図書室など世界観の**キービジュアル**）
  2. トピックに**強く依存**する動き（グラフ化、抽象シェイプ等）
  3. イントロ/アウトロ/幕間など**再利用クリップ**

---

## 4. コストモデル（初期投資→リユース）

### 4.1 8本の汎用クリップ（例）

* イントロ×3（駅/屋上/図書室）15s
* 幕間×3（抽象シェイプ）3s
* アウトロ×2（教室/図書室）12s

### 4.2 想定コスト（初回のみ）

* **Luma中心**：概算 **$2.60** 前後
* **Sora置換**：概算 **$39.00** 前後
* 以後は**再利用**で可変費ゼロ（差し替え時のみ追加）

> 実測コストはランログに記録し、ダッシュボードで**$/min・$/video**を把握。

---

## 5. 実装計画（段階導入）

### Phase 1（短期、1日）

* フォールバック連鎖を導入（Pexels→Pixabay→生成キュー投入）。
* キャッシュ層を **file + index** に分離、ヒット率計測を追加。
* プロンプト/タグ正規化を `visual_matcher` に統合。

### Phase 2（中期、~1週）

* **Luma（PiAPI）** プロバイダを実装・有効化（既定は off）。
* 8本の汎用クリップを生成・格納、**時刻/日**でローテーション。
* コスト・失敗率・一致率を**Aim/MLflow**に出力。

### Phase 3（長期、随時）

* **Sora API** 提供開始・価格確定で**高品質差し替え**の判定式を実装。
* Runwayはベンチ用。実コスト/品質が閾値を超えたら切替検討。

---

## 6. 設定（最小のYAMLで全体制御）

```yaml
# config/default.yaml
media:
  stock:
    pexels:
      enabled: true
      api_key_env: PEXELS_API_KEY
    pixabay:
      enabled: true
      api_key_env: PIXABAY_API_KEY
    cache:
      ttl_hours: 24
      lru_size: 5000
    fallback: ["pexels", "pixabay", "luma"]

  generate:
    luma:
      enabled: false
      api_key_env: LUMA_PIAPI_KEY
      max_duration_sec: 10
      resolution: "1080p"
      retry: 0

intro_outro:
  intros:
    station: "assets/video/intro_station_15s.mp4"
    rooftop: "assets/video/intro_rooftop_15s.mp4"
    library: "assets/video/intro_library_15s.mp4"
  transitions:
    - "assets/video/tr_geometric_a_3s.mp4"
    - "assets/video/tr_geometric_b_3s.mp4"
    - "assets/video/tr_geometric_c_3s.mp4"
  outros:
    classroom: "assets/video/outro_classroom_12s.mp4"
    library: "assets/video/outro_library_12s.mp4"
  select:
    intro_mode: "time_based"   # time_based|random|fixed
    outro_mode: "time_based"
```

---

## 7. 最小コード（コメント・例外処理なし）

```python
# src/services/media/ai_video_luma.py
import requests

class LumaProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.piapi.ai/luma/generate"):
        self.api_key = api_key
        self.base_url = base_url

    def generate(self, prompt: str, duration: int = 10) -> str:
        r = requests.post(self.base_url, headers={"Authorization": f"Bearer {self.api_key}"}, json={"prompt": prompt, "duration": duration})
        return r.json()["video_url"]
```

```python
# src/services/media/selector.py
from datetime import datetime
import random

def select_intro(paths: dict) -> str:
    h = datetime.now().hour
    if 5 <= h < 12: return random.choice([paths["station"], paths["rooftop"]])
    return paths["library"]

def select_outro(paths: dict) -> str:
    return paths["classroom"] if datetime.now().hour < 18 else paths["library"]
```

---

## 8. 定型クリップのプロンプト（Sora/Luma 兼用）

### 8.1 イントロ（駅ホーム 15s）

```
Morning light spreads across a quiet train platform.
Tsumugi steps forward, adjusting her bag strap and looking at the horizon.
「あさの　ひかりが　かわると、　せかいの　はなしも　すこし　かわりますね。」
She walks along the yellow line; distant train sounds.
「きょうも　たくさんの　ひとが　うごいて、　すうじが　うまれています。」
She opens her notebook; pages flutter in wind.
「その　ひとつひとつに、　いみが　かくれているかも。」
She faces camera, soft smile.
「さあ、　きょうの　ニュースを　いっしょに　みていきましょう。」
```

### 8.2 イントロ（屋上 15s）

```
Morning light across a city rooftop; laundry line moves in breeze.
Tsumugi steps into sunlight, looks up.
「ひかりが　すこし　かわりましたね。きょうの　そらは　やさしいいろです。」
She walks to the rail; distant traffic.
「ひとも　まちも、　いつも　うごいています。すうじも　その　こえの　ひとつです。」
Wind rises; notebook pages flutter.
「でも　きょうの　いみを　つくるのは、　いまを　みている　わたしたちです。」
She smiles to horizon.
「さあ、　あたらしいいちにちを　いっしょに　はじめましょう。」
```

### 8.3 イントロ（図書室 15s）

```
A quiet library after sunset; warm desk lamp.
Tsumugi turns a page, glances to window lights.
「よるの　まちって、　ちょっと　ほっとしますね。」
She sets down her pen; clock hand moves slowly.
「きょうも　たくさんの　できごとが　すぎていきました。すうじも　その　きおくの　ひとつです。」
She closes the book; dust motes.
「でも　そのなかに、　あしたを　つくる　ヒントが　かくれているのかも。」
She looks at camera.
「いっしょに　みつけに　いきましょう。　きょうのニュースです。」
```

### 8.4 幕間（抽象 3s）

```
Metallic silver and deep blue geometric shapes rotate in dark gradient space.
Subtle motion blur; shapes align into a grid and dissolve into particles.
3 seconds. 1080p.
```

### 8.5 アウトロ（教室 12s）

```
Late afternoon classroom; golden sunlight across desks.
Tsumugi closes notebook, looks to window.
「きょうの　ニュース、　どうでしたか？」
She traces light on glass.
「すうじの　むこうに　ひとが　いて、　ものがたりが　ある。　それを　かんじられたら　うれしいです。」
Faces camera with soft smile.
「また　あした、　あたらしい　はっけんを　いっしょに。」
```

### 8.6 アウトロ（図書室 12s）

```
Closing time library; warm lamp glow.
Tsumugi stacks books, walks toward camera.
「きょうも　いろんな　かずが　ありましたね。　でも　それは　ぜんぶ　ひとの　いとなみです。」
She stops at doorway, turns off lamp.
「それじゃ、　また　つぎの　ニュースで。　おつかれさまでした。」
```

### 8.7 ショート用告知（10–12s）

```
Evening light through classroom window.
Tsumugi closes notebook, faces camera.
「きょうの　はなし、　もうすこし　ききたいなって　おもったら……」
Soft smile, small nod.
「つづきは　ユーチューブの　びょうそくマネーチャンネルで　おまちしています。」
```

---

## 9. 品質基準とKPI

| 指標        | 定義                 | 目標      |
| --------- | ------------------ | ------- |
| 一致率       | 台本タグと映像の主題一致度      | ≥ 0.8   |
| 平均生成コスト   | $/video（再利用除く）     | 低下トレンド  |
| 失敗率       | 生成・DL・合成の失敗割合      | ≤ 2%    |
| 視聴維持率     | 0–15s/ラスト10sの残存率   | 前回比 +x% |
| キャッシュヒット率 | 素材リクエストに対するキャッシュ命中 | ≥ 70%   |

> すべて日次集計・可視化。しきい値割れでSlack通知。

---

## 10. 運用・法務・表記

* YouTube では **AI生成コンテンツの明示**を継続（概要欄・Studio設定）。
* ストック素材は各ライセンス遵守（Pixabayはホットリンク禁止、Pexelsは表記不要だが推奨明記）。
* 生成物の二次配布可否は各サービスの最新版規約を都度確認。
* 固有名詞・ブランド露出は**差し替え可能なバージョン**を保持。

---

## 11. チェックリスト

**ストックAPI**

* [ ] Pexels/Pixabayキー設定
* [ ] 24h + LRUキャッシュ
* [ ] 自動フォールバック連鎖
* [ ] ヒット率/一致率ログ

**生成系**

* [ ] Lumaプロバイダ実装
* [ ] 8本の汎用クリップ生成・格納
* [ ] コスト・失敗率・台本一致率の計測
* [ ] Sora/RWYの定期ベンチ

**合成**

* [ ] イントロ/幕間/アウトロ自動挿入
* [ ] TTSは別トラックで合成
* [ ] 音量ノーマライズ（LUFS）

---

## 12. 付録：最小合成コマンド

```bash
ffmpeg -i intro.mp4 -i main.mp4 -i outro.mp4 \
-filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]" \
-map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 23 -c:a aac out.mp4
```

TTS重畳:

```bash
ffmpeg -i visual.mp4 -i voice.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac merged.mp4
```

