# Prompt & Output Strategy: @byosan-money (Target: Over 40s)

**Date**: 2025-12-06
**Objective**: Redesign output schemas to generate high-quality, "Executive Briefing" style content for busy professionals, while automatically generating assets for X (Twitter), LinkedIn, and Hatena Blog.

---

## 2. Output Schema Strategy (JSON)

We will expand the LLM output to include **Social Media Assets** directly from the generation phase.

### 2.1 Unified Output Object
The `ScriptGenerator` step will now output a richer JSON structure:

```json
{
  "social_content": {
    "twitter": {
      "post_text": "日経平均は大幅続落📉 米国金利の上昇が重石に。\n\n40代からの資産防衛術、今日の動画で解説しました。\n#日経平均 #新NISA\n[VIDEO_LINK]",
      "image_prompt": "A sharp downward red stock chart on a sleek black background, professional financial style"
    },
    "linkedin": {
      "post_text": "【本日の市況: 米国金利と日本株の相関】\n\n本日の日経平均株価は500円安となりました。主な要因は...\n\n1. 米国10年債利回りの上昇\n2. 半導体セクターの利益確定売り\n\n私たち40代の投資家が今すべき「守り」の戦略について、動画で詳しく解説しています。\n\n#Investment #JapanMarket #AssetManagement",
      "slide_content": [
        "Slide 1: Title - Today's Market Drop",
        "Slide 2: Key Factor - US Yields",
        "Slide 3: Action - Defensive Rotation"
      ]
    },
    "hatena_blog": {
      "title": "【12/6市況】日経平均続落。40代が今見直すべきポートフォリオとは？",
      "tags": ["株式投資", "資産運用", "市況解説"],
      "category": "市況ニュース"
    }
  }
}
```