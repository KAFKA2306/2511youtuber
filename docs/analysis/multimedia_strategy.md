# Multimedia Strategy: @byosan-money (Target: Over 40s)

**Date**: 2025-12-06
**Objective**: Expand "Byosan Money" from YouTube to a multi-platform ecosystem targeting busy professionals (Over 40s), utilizing full API automation.

---

### 2.3 Platform Selection & Rationale

| Platform | Role | API Status | Target Match (Over 40s) | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **YouTube** | **Core Hub** | Official (v3) | High | **Primary** |
| **X (Twitter)** | **Speed Layer** | Official (v2) | High (News consumption) | **Selected** |
| **LinkedIn** | **Trust Layer** | Official (v2) | High (Professional) | **Selected** |
| **Hatena Blog** | **Knowledge Layer** | **Official (AtomPub)** | **High (Tech/Finance literate)** | **Selected** |

> [!NOTE]
> **Why Hatena?**
> Hatena Blog offers a robust, official AtomPub API and has a demographic (30s-50s, high income) that perfectly matches our "Asset Defense" strategy.

---

## 1. Platform Ecosystem

| Platform | Role | Target Audience | Content Type | API Status |
| :--- | :--- | :--- | :--- | :--- |
| **YouTube** | **Core Hub** | General / Mass | Video (Long & Shorts) | Existing (`apps.youtube`) |
| **X (Twitter)** | **Breaking News** | Traders / News Junkies | Text + Chart Images | API v2 (Basic Tier rec.) |
| **Hatena Blog** | **Archive / SEO** | Search Users / Readers | Full Transcript + Links | AtomPub API (Free) |
| **LinkedIn** | **Executive Briefing** | **Over 40s / Business** | Professional Summary | Share API (Personal) |

---

## 2. Detailed Strategy per Platform

### 2.1 X (Twitter) - "The Speed Layer"
*   **Strategy**: "Byosan" means speed. Post market updates *before* the video is ready.
*   **Content**:
    *   **Market Open/Close**: Automated posting of Nikkei/Dow values.
    *   **Video Teaser**: "New video up: Why the Yen dropped today. [Link]"
    *   **Charts**: Image uploads of the day's key graph.
*   **API Implementation**:
    *   **Tier**: **Basic Tier ($100/mo)** is recommended for stability (50,000 posts/mo).
    *   **Free Tier**: Limited to 1,500 posts/mo (~50/day). Viable for *just* video notifications, but risky for high-frequency market updates.
    *   **Automation**: Use `tweepy` or direct HTTP requests.

### 2.2 Hatena Blog - "The Knowledge Layer"
*   **Strategy**: SEO dominance. Video content is invisible to Google Search text crawlers. Hatena Blog fixes this.
*   **Content**:
    *   **Full Transcript**: Convert the video script (from `script.json`) into a readable blog post.
    *   **Keywords**: "Nikkei Forecast", "NISA Strategy", "High Dividend Stocks".
    *   **Affiliate**: Place relevant affiliate links (books, brokerage accounts) in the text.
*   **API Implementation**:
    *   **Protocol**: **AtomPub**. Standard, robust, and free.
    *   **Auth**: WSSE or OAuth.
    *   **Workflow**: `Video Generated` -> `Script to Markdown` -> `Post to Hatena`.

### 2.3 LinkedIn - "The Trust Layer" (New for Over 40s)
*   **Strategy**: "Executive Briefing". Over 40s are on LinkedIn for *career and industry news*, not entertainment.
*   **Content**:
    *   **Professional Tone**: "Today's market impact on Japanese manufacturing..." (No "Yukkuri" jokes).
    *   **Slide Deck**: Export video keyframes as a PDF Carousel (LinkedIn loves PDF sliders).
*   **API Implementation**:
    *   **Endpoint**: `v2/ugcPosts` or `v2/shares`.
    *   **Limit**: ~25 posts/day (Personal Profile). Sufficient for a daily summary.
    *   **Auth**: OAuth 2.0 (Requires periodic token refresh).

---

## 3. Automation Architecture

```mermaid
graph TD
    A[NewsCollector] --> B[ScriptGenerator]
    B --> C[VideoRenderer]
    
    B --> D{Content Repurposing}
    
    D --> E[X (Twitter)]
    E -->|Text + Image| E1[Breaking News]
    
    D --> F[Hatena Blog]
    F -->|Markdown| F1[SEO Article]
    
    D --> G[LinkedIn]
    G -->|PDF/Text| G1[Executive Summary]
    
    C --> H[YouTube]
```

## 4. Next Steps

1.  **API Keys**: Apply for Twitter Basic (or Free) and LinkedIn Developer App.
2.  **Hatena Auth**: Get API Key from Hatena account settings.
3.  **Development**:
    *   Create `src/steps/social/twitter.py`
    *   Create `src/steps/social/hatena.py`
    *   Create `src/steps/social/linkedin.py`
