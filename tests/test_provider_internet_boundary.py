import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def completion_calls(path: Path, class_name: str, method_name: str) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    return [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "litellm"
        and node.func.attr == "completion"
    ]


def keyword_names(call: ast.Call) -> set[str]:
    return {keyword.arg for keyword in call.keywords if keyword.arg is not None}


class ProviderInternetBoundaryTest(unittest.TestCase):
    def test_news_gemini_is_the_only_gemini_path_with_search_tool(self) -> None:
        news_path = ROOT / "src" / "providers" / "news.py"
        llm_path = ROOT / "src" / "providers" / "llm.py"

        news_calls = completion_calls(news_path, "GeminiNewsProvider", "execute")
        selection_calls = completion_calls(news_path, "GeminiNewsProvider", "select_news")
        llm_calls = completion_calls(llm_path, "GeminiProvider", "_try_execute_with_model")

        self.assertEqual(len(news_calls), 1)
        self.assertEqual(len(selection_calls), 1)
        self.assertEqual(len(llm_calls), 1)
        self.assertIn("tools", keyword_names(news_calls[0]))
        self.assertNotIn("tools", keyword_names(selection_calls[0]))
        self.assertNotIn("tools", keyword_names(llm_calls[0]))

        tools = next(keyword.value for keyword in news_calls[0].keywords if keyword.arg == "tools")
        self.assertIsInstance(tools, ast.List)
        self.assertEqual(len(tools.elts), 1)
        self.assertIn("googleSearch", ast.unparse(tools.elts[0]))


if __name__ == "__main__":
    unittest.main()
