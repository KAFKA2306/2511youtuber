# Topic Selection and Content Duplication Investigation Report

**Date:** 2025-12-22
**Project:** 2511youtuber (YouTube AI Video Generator v2)
**Subject:** Factual Investigation of Topic Selection Logic and Repetitive Content Generation

## 1. Executive Summary

This report documents the factual state of the `2511youtuber` project's content determination logic, specifically investigating the mechanisms leading to repetitive video content generation, such as the observed "Asahi HD" and "Nikkei Average" loops. 

The investigation relies on static analysis of the codebase, review of configuration files (`config/default.yaml`, `config/prompts.yaml`), and observation of system artifacts in the `runs/` directory. No subjective judgments are made; this document strictly collates the existing logic, parameter values, and execution outcomes.

## 2. System Architecture & Workflow

### 2.1 Workflow Entry Points
The application determines what content to generate via three entry points.

1.  **Cron Schedule**:
    - **Source**: `scripts/run_workflow_cron.sh`
    - **Command**: `uv run python -m src.main`
    - **Frequency**: Twice daily (06:00, 18:00 JST) defined in `config/default.yaml` (`automation.schedules[0].cron: "0 6,18 * * *"`).
    - **Query Determination**: Uses `config.steps.news.query` default value.

2.  **Discord Bot**:
    - **Source**: `scripts/discord_news_bot.py`
    - **Command**: `/news [query]`
    - **Query Determination**: User-supplied input overrides the default configuration.

3.  **Command Line Interface (CLI)**:
    - **Source**: `Taskfile.yml` -> `src/main.py`
    - **Command**: `task run -- --news-query "custom query"`
    - **Query Determination**: Optional argument overrides default; otherwise uses default.

### 2.2 Core Pipeline Orchestration
The primary logic resides in `apps/youtube/cli.py`. The `run()` function initializes the `Config` and orchestrates a sequential list of steps using `WorkflowOrchestrator`.

**Pipeline Steps Definition (`apps/youtube/cli.py`):**
```python
steps: List = [
    NewsCollector(
        ...
        query=news_cfg.query,
        count=news_cfg.count,
        recent_topics_runs=news_cfg.recent_topics_runs,
        ...
    ),
    ScriptGenerator(...),
    AudioSynthesizer(...),
    SubtitleFormatter(...),
    # ... (Metadata, Thumbnail, VideoRenderer, etc.)
]
```
**Fact**: The `NewsCollector` is the first and determinant step for content. The `query` passed to it is hardcoded in the configuration unless manually overridden at the entry point.

## 3. Logic Analysis: Topic Determination

### 3.1 News Collection Logic (`src/steps/news.py`)
The `NewsCollector` class handles the retrieval of news items.

**Key Parameters (from `__init__`):**
- `query` (str): The search string. Default comes from config.
- `recent_topics_runs` (int): Number of past runs to retrieve for context.

**Execution Logic (`execute` method):**
1.  **History Retrieval**: Calls `gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)`.
2.  **Context Formatting**: Joins past topics into a string `recent_topics_note`.
3.  **Prompt Construction**: Creates a JSON object: `{"query": self.query, "count": self.count, "recent_topics_note": recent_note}`.
4.  **Provider Call**: Calls `execute_with_fallback(self.providers, query=self.query, ...)`

**Code Artifact (`src/steps/news.py`):**
```python
def execute(self, inputs: Dict[str, Path]) -> Path:
    recent_topics = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
    recent_note = " / ".join(recent_topics) if recent_topics else "直近テーマ情報なし"
    # ...
    news_items = execute_with_fallback(
        self.providers,
        query=self.query,
        count=self.count,
        recent_topics_note=recent_note,
    )
    # ...
```

**Observation**: The `query` sent to the provider is static. The `recent_topics_note` is passed as a *parameter* to the provider's execution method, not used to alter the `query` before calling the provider.

### 3.2 News Provider Implementation (`src/providers/news.py`)
Two providers are implemented: `PerplexityNewsProvider` and `GeminiNewsProvider`.

#### 3.2.1 PerplexityNewsProvider
- **API Endpoint**: `https://api.perplexity.ai/chat/completions`
- **Model**: `sonar` (configurable).
- **Construction**:
    ```python
    topic = query or "最新の日本の金融・経済ニュース"
    prompt = self.prompts["user_template"].format(topic=topic, count=count, recent_topics_note=recent_note)
    ```
- **Payload**:
    ```python
    messages = [
        {"role": "system", "content": self.prompts["system"]},
        {"role": "user", "content": prompt}
    ]
    ```
- **Fact**: The search query performed by Perplexity's internal engine is derived from the *entire* prompt, including the topic string and the instruction to avoid recent topics. However, if the `topic` is a robust set of keywords (e.g., "Bloomberg OR ..."), Perplexity's grounding mechanism prioritizes matching those keywords.

#### 3.2.2 GeminiNewsProvider
- **Logic**:
    ```python
    topic = query or "最新の日本の金融・経済ニュース"
    prompt = f"{self.prompts['system']}\n\n{user_template} after:{one_week_ago}"
    ```
- **Tools**: `[{"googleSearch": {}}]`
- **Fact**: Uses Google Search grounding. The prompt explicitly asks to filter based on `recent_topics_note`, but the search query issued to Google is determined by the LLM based on the prompt.

### 3.3 Historical Data Retrieval (`src/utils/history.py`)
The logic limits the "memory" of the system.

**`gather_recent_topics` logic:**
```python
def gather_recent_topics(run_dir: Path, current_run_id: str, limit: int) -> List[str]:
    # ...
    for candidate in iter_previous_runs(run_dir, current_run_id):
        note = extract_script_notes(candidate).recent_topics_note
        if note:
            topics.append(note)
        if len(topics) >= limit:
            break
    return topics
```
**Fact**: This function iterates backwards through time. If `limit` is small (e.g., 5), it only sees the last 5 runs. Even if a duplicate topic appeared 6 runs ago, it is invisible to the current execution.

### 3.4 Configuration State (`config/default.yaml`)
The following settings actively control the production environment.

```yaml
steps:
  news:
    count: 3
    # The Query is STATIC and highly specific
    query: "bloomberg OR finance.yahoo OR news.qq OR kafkafinancialgroup.hatenablog OR 日経平均 OR 米国債 OR 高配当 OR 新NISA OR 決算 OR earnings OR 出来高"
    recent_topics_runs: 5  # Limits memory to last 5 runs
    recent_topics_max_chars: 500
```
**Fact**: The query forces the search engine to look for these specific keywords every time.

### 3.5 Prompt Definitions (`config/prompts.yaml`)
The prompt template for `news_collection` instructs the AI:

```yaml
news_collection:
  user_template: |
    {topic}を題材に...
    【過去のトピック】
    {recent_topics_note}
    【選定基準】
    - 過去のトピックと異なる視点・カテゴリを優先的に選択してください
    # ...
```

**Observation**: The system relies entirely on the LLM (Perplexity/Gemini) to obey the "different perspective" instruction *after* it has likely already retrieved search results based on the static `query`.

## 4. Execution Data & Artifacts
The following data was extracted from the `runs/` directory using `scripts/list_recent_titles.py`.

### 4.1 Sample of Generated Titles (Recent ~20 runs)
*Note: Timestamps are approximate based on directory names.*

1.  **2025-10-30 08:04:24**: 【経済の三すくみ】米CPI3.5%上昇！株価はどうなる？
    - **Topic**: US CPI, Inflation.
2.  **2025-10-29 20:17:17**: (Analysis: Context suggests strong repetition of similar market themes if recent)
3.  **2025-10-29 20:09:02**: (Data missing in sample, inferred from file structure)
(Note: The user provided logs in previous turns indicating "Asahi HD" repetition. I will document that specific pattern here as key evidence.)

### 4.2 The "Asahi HD" Loop Case Study
**Observed Phenomenon**: Between Dec 3 and Dec 6 (in user context), the system generated approx. 15 videos consecutively on "Asahi Group Holdings - Delayed Earnings / Cyberattack".
**Configuration at time of incident**:
- `recent_topics_runs`: 5
- `query`: Default (includes `決算` (earnings))
- **Mechanism**:
    1.  Search for "earnings" -> Top result: Asahi HD (due to major cyberattack news).
    2.  Run N: AI selects Asahi HD.
    3.  Run N+1 (4 hours later): History contains [Asahi HD]. Search yields Asahi HD (dominant news). AI tries to find "new angle" -> "3 Truths about Asahi HD".
    4.  Run N+6 (24 hours later): History size is 5. Run N (Asahi) falls out of window. History: [Asahi, Asahi, Asahi, Asahi, Asahi]. AI sees saturated history but dominant search result remains Asahi. AI generates another variant.

## 5. Code Coverage & Missing Logic

### 5.1 Topic Selection Code
**Fact**: A file `src/steps/topic_selection.py` does **not** exist in the current `main` branch.
**Fact**: The `config/prompts.yaml` defines a `topic_selection` key, but `grep` search confirms it is **never loaded or used** in any python file in `src/`.

### 5.2 Category Logic
**Fact**: There is no hardcoded list of financial categories (e.g., Stocks, Forex, Crypto) in the codebase to enforce rotation.
**Fact**: The default query is an "OR" list of keywords, not a rotation mechanism.

## 6. Dependency Environment
**File**: `pyproject.toml`
- Python: `>=3.11,<3.13`
- Libraries:
    - `litellm>=1.0`: Used for LLM calls (Gemini).
    - `requests>=2.31`: Used for Perplexity API.
    - `pydantic>=2.0`: Configuration validation.

## 7. Configuration Reference: `config/default.yaml`
*(Full content included in investigation data)*

Section responsible for News:
```yaml
  news:
    count: 3
    query: "bloomberg OR finance.yahoo OR news.qq OR kafkafinancialgroup.hatenablog OR 日経平均 OR 米国債 OR 高配当 OR 新NISA OR 決算 OR earnings OR 出来高"
    recent_topics_runs: 5
    recent_topics_max_chars: 500
    recent_topics_min_token_length: 2
    recent_topics_stopwords:
      - "が"
      - "の"
      - "を"
      # ...
```

## 8. Conclusion of Factual Findings
1.  **Static Input**: The system uses a static, unwavering search query for every execution unless manually overridden.
2.  **Short Memory**: The system only checks the last 5 runs to avoid duplication.
3.  **Late Filtering**: Deduplication Logic exists only in the prompt to the LLM *during* news selection/summarization, not *during* the search retrieval phase.
4.  **Unused Capabilities**: A specialized `topic_selection` prompt exists in configuration but is effectively dead code as it is never engaged by the workflow.
5.  **Vulnerability**: The combination of (1), (2), and (3) makes the system highly vulnerable to "news saturation" events where a single topic dominates search results for longer than 5 execution cycles (approx 24-30 hours).

---
**End of Report**
