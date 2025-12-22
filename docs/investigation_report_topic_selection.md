# Topic Selection and Content Duplication Investigation Report

## 1. Overview
This report documents the factual state of the `2511youtuber` project's topic selection mechanism, specifically investigating the causes behind repetitive content generation (e.g., the "Asahi HD" loop). It details the system architecture, code logic, configuration settings, and observed execution results.

## 2. System Architecture & Workflow

### 2.1 Entry Points
The workflow is triggered via three primary methods:
1.  **Cron Schedule (`scripts/run_workflow_cron.sh`)**: Runs at 06:00 and 18:00 JST. Uses default configuration.
2.  **Discord Bot (`scripts/discord_news_bot.py`)**: User triggers via `/news [query]`.
3.  **CLI (`src/main.py`)**: Manual execution via `task run`.

### 2.2 Core Logic Components
The content generation pipeline (`apps/youtube/cli.py`) consists of the following sequential steps:
1.  **NewsCollector**: Retrieves news based on a query.
2.  **ScriptGenerator**: Generates a script from the news.
3.  **AudioSynthesizer**: Generates audio.
4.  **VideoRenderer**: Generates video.

### 2.3 Data Persistence
- **Run Directory**: `runs/{YYYYMMDD_HHMMSS}/`
- **Artifacts**: `news.json` (collected news), `script.json` (generated script), `metadata.json` (video metadata).
- **History Tracking**: `src/utils/history.py` scans `runs/` directory to retrieve past topics.

## 3. Detailed Logic Analysis

### 3.1 News Collection (`src/steps/news.py`)
- **Class**: `NewsCollector`
- **Input**:
    - `query`: Search string (default from config).
    - `recent_topics_runs`: Number of past runs to check for duplicates.
- **Provider Execution**: Calls `execute_with_fallback` on configured providers (Perplexity, Gemini).
- **History logic**:
    - Calls `gather_recent_topics` to get a list of past titles.
    - Formats this list into a string `recent_topics_note`.
    - **CRITICAL FACT**: The `query` passed to the provider is static (default config) unless overwritten by CLI args. The `recent_topics_note` is passed as *context* to the LLM prompt, not as a hard filter for the search API itself.

### 3.2 Provider Implementation (`src/providers/news.py`)
- **PerplexityNewsProvider**:
    - **API**: `https://api.perplexity.ai/chat/completions`
    - **Model**: `sonar` (default)
    - **Prompt Construction**: Uses `prompts.yaml` -> `news_collection` -> `user_template`.
    - **Fact**: The search query sent to Perplexity's internal search engine depends on how the model interprets the user prompt. The code sends the `query` variable as part of the prompt string: `"{topic}を題材に..."`.
    - **Fact**: If `topic` is the broad default query ("bloomberg OR ..."), Perplexity performs a broad search.
    - **Fact**: `search_recency_filter` is configurable (default: `week`).

- **GeminiNewsProvider**:
    - **Tool**: `googleSearch` tool.
    - **Prompt**: Specifically appends `after:{one_week_ago}` to the prompt.
    - **Fact**: Relies on Google Search grounding.

### 3.3 History & Deduplication (`src/utils/history.py`)
- **Function**: `gather_recent_topics`
- **Logic**: Iterates through `runs/` directory in reverse chronological order.
- **Extraction**: Reads `script.json` (notes) or `metadata.json`/`youtube.json` (title).
- **Limit**: Controlled by `limit` argument (default: 5).
- **Fact**: Only retrieves the *titles* of past videos. It does not retrieve the full list of news URLs or specific news items used.

### 3.4 Configuration State (`config/default.yaml`)
- **Default Query**: `"bloomberg OR finance.yahoo OR news.qq OR kafkafinancialgroup.hatenablog OR 日経平均 OR 米国債 OR 高配当 OR 新NISA OR 決算 OR earnings OR 出来高"`
- **Recent Topics Runs**: `5`
- **News Count**: `3`
- **Prompt Definition** (`config/prompts.yaml`):
    - `news_collection/user_template`: Instructs AI to select news based on the topic and exclude `recent_topics_note`.
    - **Fact**: Contains a `topic_selection` section defining a task to "select a new topic category used in the past".
    - **Fact**: **`topic_selection` section is NOT used in the codebase**. Grep search confirmed zero usages of `topic_selection` key in `src/`.

## 4. Observed Behavior & Data

### 4.1 Recent Run Log (Titles)
A strict chronological list of generated video titles (truncated to recent 70):

**Pattern A: "Asahi HD" Loop (Dec 3 - Dec 6)**
- 12/06 08:00: アサヒG 決算50日延期！サイバー攻撃で露呈した3つの真実
- 12/06 04:00: アサヒHD決算50日超延期！サイバー攻撃の裏にある3つの真実
- 12/06 00:00: アサヒ決算50日超延期！サイバー攻撃が暴く3つの真実
- 12/05 20:00: アサヒグループ決算50日超延期！サイバー攻撃の裏に潜む3つの真実
- 12/05 16:00: アサヒG決算50日超延期！サイバー攻撃の裏に隠された3つの真実
... (Total ~15 repetitions)

**Pattern B: "Nikkei Average" Loop (Dec 6 - Dec 22)**
- 12/22 18:00: 日経平均5万402円回復！半導体株牽引の年末戦略
- 12/22 06:00: 日経平均、週次1329円下落！5万円台回復の壁と年末戦略
- 12/21 18:00: 日経平均5万円割れ警戒！S&P500半導体で上昇
...

### 4.2 Repetition Mechanics
1.  **Trigger**: The Cron job fires at fixed intervals (6h or 12h), or manual bursts occur (e.g., 4-hour intervals observed on Dec 3-6).
2.  **Search**: `NewsCollector` executes with the *static default query*.
3.  **Result Retrieval**: The search provider (Perplexity/Google) returns the currently most "relevant" or "popular" news matching the query. During Dec 5-6, "Asahi HD delayed earnings due to cyberattack" was likely the dominant signal in the search index for "earnings" or "finance".
4.  **Filtering Attempt**:
    - The code fetches the last 5 titles.
    - Example Context passed to AI: "Recent topics: Title A, Title B, Title C, Title D, Title E".
    - If the "Asahi" runs were frequent (every 4 hours), the 6th run ago (24 hours ago) drops out of the list.
    - AI sees the search result "Asahi HD..." and checks the exclusion list.
    - Even if "Asahi" is in the exclusion list, if *all* top search results are about Asahi (due to search volume), the AI is forced to process it. It attempts to "find a new angle" (e.g., focusing on "3 truths" or "profit maintenance" vs "leakage"), resulting in titles that look different to the AI but are identical to the user.

## 5. Metadata & Artifact Analysis

### 5.1 `runs/` Structure
- Directories are named by timestamp: `YYYYMMDD_HHMMSS`.
- Successful runs contain `render_video.mp4` and `metadata.json`.

### 5.2 Title Generation Pattern
- Observed high frequency of specific phrasings:
    - "3つの真実" (3 Truths)
    - "裏側" (Behind the scenes)
    - "衝撃" (Impact/Shock) - despite "shock" being in forbidden words list (`config/prompts.yaml` prohibits `ショック`, `衝撃` in title/description? No, strictly checked: `metadata:tone:title_disallowed_terms` includes `衝撃`. However, titles like `日経平均700円安の衝撃！` exist.
    - **Fact**: The forbidden word check might be implemented *after* generation or is soft-guidance in the prompt. `metadata/model.py` or `steps/metadata.py` logic needs verification for enforcement.

## 6. Codebase Gaps

### 6.1 Missing Logic
- **Dynamic Query Generation**: There is no code that generates a specific search query based on history. The `query` is hardcoded or user-provided.
- **Topic Rotation**: No mechanism exists to cycle through different financial sectors (e.g., Crypto -> Forex -> Stocks).
- **Strict Deduplication**: Deduplication relies purely on the LLM's context window ("Here are past topics, don't repeat"). There is no string-matching or semantic similarity check on the *content* of the retrieved news URLs against past runs.

### 6.2 Unused Resources
- `config/prompts.yaml` -> `topic_selection`: Defined but never loaded or executed.
- `src/utils/history.py`: Retrieves titles but `NewsCollector` doesn't use them to *change* the search strategy, only to *inform* the summarization.

## 7. Configuration Details
- **`default.yaml`**:
    - `recent_topics_runs`: 5. (Too short for frequent runs)
    - `steps.news.query`: Very broad OR-based query.

## 8. Conclusion
The "Asahi HD" and "Nikkei Average" loops are the direct result of:
1.  **Static, broad search queries** leading to identical search results for extended periods.
2.  **Insufficient history lookback** (5 runs) causing known topics to expire from the exclusion list quickly.
3.  **Lack of pre-search topic selection**, forcing the AI to filter *after* search rather than *before*.
4.  **Ineffective exclusion prompts** when search results are homogenous.

This report summarizes the factual findings as of 2025-12-22.
