## 提案7：音声の感情表現強化

### 現状
VOICEVOXは2025年10月時点で**SSMLに非対応**です。[1][3][10]

### 実装方法

**プロンプトに追加**:
```yaml
# prompts.yaml の script_generation
各セリフの末尾に音声制御タグを付与:
[VOICE: speed=1.2, pitch=0.05, intonation=1.5]

例:
「マジでヤバいっしょ [VOICE: speed=1.3, pitch=0.1, intonation=1.8]」
「営業利益率が5%低下です [VOICE: speed=0.8, pitch=-0.05, intonation=0.7]」
```

**Pythonで処理**:
```python
import re
def parse_voice(text):
    match = re.search(r'\[VOICE: speed=([\d.]+), pitch=([-\d.]+), intonation=([\d.]+)\]', text)
    if match:
        return {
            'text': re.sub(r'\[VOICE:.*?\]', '', text),
            'speedScale': float(match.group(1)),
            'pitchScale': float(match.group(2)),
            'intonationScale': float(match.group(3))
        }
```

VOICEVOXの`audio_query`エンドポイントに上記パラメータを渡します。[3][10]

### 今実装していない理由

LLMで生成した音声制御タグの表記違いによるバグ、エラーが発生し、プロンプトと構造の調整で闇雲に時間を浪費するリスクがある。
一方で、LLMの性能が十分であるなら、ぜひ実装したい機能の一つだ。

---

## 提案8：パフォーマンスフィードバックループ

### 実装手順

**1. データ取得（Python）**:
```python
from googleapiclient.discovery import build

def fetch_metrics(youtube_analytics, video_id, start_date, end_date):
    return youtube_analytics.reports().query(
        ids='channel==MINE',
        startDate=start_date,
        endDate=end_date,
        metrics='views,likes,averageViewDuration,estimatedMinutesWatched',
        filters=f'video=={video_id}'
    ).execute()
```

取得可能: 再生回数、高評価、平均視聴時間、総視聴時間。[11][12][13]
**CTRは取得不可**（YouTube Studioから手動エクスポート必要）。[14][15]

**2. データベース保存**:
```sql
CREATE TABLE performance (
    video_id TEXT,
    views INT,
    avg_duration REAL,
    topic TEXT
);
```

**3. 成功パターン抽出**:
```python
# 高維持率トピックを抽出
query = '''
SELECT topic, AVG(avg_duration) as retention
FROM performance
GROUP BY topic
HAVING retention > (SELECT AVG(avg_duration) FROM performance)
ORDER BY retention DESC LIMIT 5
'''
```

**4. プロンプトに反映**:
```yaml
# prompts.yaml に追加
【過去の成功パターン】
{success_patterns}

例:
- 具体的企業名を含む議論 → 平均維持率68%
- 視聴者への問いかけ3回以上 → コメント数1.8倍
```

これにより、AIが高パフォーマンスパターンを学習し、自動的に反映するようになります。

### 今実装していない理由

ある程度成功事例がないと、特に有益なフィードバックループを回せない。
一方で、将来的には必須機能であり、ある程度、成功事例、失敗事例、チャンネル全体の整合性などを積み重ねてから実装する余地あり。







---


## 提案11：字幕タイミングの精度向上

### 現状の課題
`SubtitleFormatter`は文字数比率で時刻を配分しており、実際の音声と字幕がズレます。[2][1]

### 実装方法

**`src/steps/subtitle.py`を改訂**:
```python
def align_with_audio(audio_path: Path, segments: List[ScriptSegment]) -> List[SubtitleEntry]:
    from pydub import AudioSegment
    
    audio = AudioSegment.from_wav(audio_path)
    total_duration = len(audio) / 1000.0  # ms → s
    
    # 無音区間を検出し、セグメント境界として使用
    silences = detect_silence(audio, min_silence_len=300, silence_thresh=-40)
    
    # 各セグメントを無音区間で区切る
    timings = calculate_timings(segments, silences, total_duration)
    return timings
```

**依存追加**:
```toml
# pyproject.toml
dependencies = [
    "pydub>=0.25.1",
]
```

**効果**: 字幕と音声のズレが解消され、視聴体験が大幅に改善されます。

### 今実装していない理由

実際に、字幕のずれは少しだけある。切り替わりが1秒くらい早い。ただ、許容範囲だ。致命的ではない。

***

## 提案14：プロンプトバージョン管理

### 現状の課題
`prompts.yaml`を変更すると、過去の動画との整合性が失われます。[1]

### 実装方法

**バージョン付きプロンプト**:
```
config/
└── prompts/
    ├── v1.0.yaml  # 初版
    ├── v1.1.yaml  # 改訂版
    └── latest.yaml → v1.1.yaml  # シンボリックリンク
```

**`workflow_state.json`に記録**:
```json
{
  "run_id": "20251013_1600",
  "prompt_version": "v1.1",
  "completed_steps": ["news", "script"]
}
```

**効果**: 動画ごとに使用したプロンプトが記録され、A/Bテストや品質分析が可能になります。

# 今実装していない理由

特にない。実験管理的にプロンプトとその効果を科学的に検証して、蓄積していく体制があるといい。
一方で抱えきれないほどのプロジェクト肥大化にならないように注意深く進める必要がある。LLMのコンテクストを超えてしまうと、その他の改修ができなくなってしまうため、肥大化にはリスクがある。