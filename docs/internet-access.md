# インターネットアクセス境界

このリポジトリでは、Gemini利用を「Web検索を行うニュース取得」と「与えられた入力だけを処理する生成」に分離する。

| 経路 | Provider | Web検索 | 入力 |
| --- | --- | --- | --- |
| news collection | `GeminiNewsProvider.execute` | 有効 | 検索query |
| news selection | `GeminiNewsProvider.select_news` | 無効 | 取得済み候補 |
| script generation | `GeminiProvider` | 無効 | 取得済みニュース |
| metadata generation | `GeminiProvider` | 無効 | 取得済みニュースとscript |
| news collection | `PerplexityNewsProvider` | Perplexity API | 検索query |

`GeminiNewsProvider.execute` だけが `litellm.completion(..., tools=[{"googleSearch": {}}])` を渡す。`GeminiNewsProvider.select_news` と `GeminiProvider` は `tools` を渡さない。この境界は `tests/test_provider_internet_boundary.py` で検証する。

GoogleのGemini APIではGoogle Search groundingは明示的な検索toolとして提供され、現在の公式ドキュメントでは `google_search` を有効化するとリアルタイムWebコンテンツを検索してgrounded responseを生成する。実装上のLiteLLM表記とGoogle SDK/RESTの表記は同一であるとは仮定せず、このリポジトリでは実際のprovider呼び出し形をテスト対象にする。

一次情報: https://ai.google.dev/gemini-api/docs/google-search
