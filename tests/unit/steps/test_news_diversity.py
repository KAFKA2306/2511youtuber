from __future__ import annotations

from pathlib import Path

from src.models import NewsItem
from src.steps.news import NewsCollector


class FakeSelectorProvider:
    name = "fake-selector"
    model = "fake-selector-v1"

    def is_available(self) -> bool:
        return True

    def select_news(self, *, prompt: str) -> str:
        assert "candidate" in prompt
        return (
            '{"selections": ['
            '{"index": 1, "reason": "為替を選ぶ"}, '
            '{"index": 2, "reason": "商品を選ぶ"}, '
            '{"index": 3, "reason": "暗号資産を選ぶ"}'
            ']}'
        )


class FakeUnavailableSelector:
    name = "offline"

    def is_available(self) -> bool:
        return False

    def select_news(self, *, prompt: str) -> str:
        raise AssertionError("unavailable selector must not be called")


def _items() -> list[NewsItem]:
    return [
        NewsItem(title="日経平均株価が上昇", summary="日本株", url="https://example.test/nikkei"),
        NewsItem(title="ドル円が動く", summary="為替", url="https://example.test/fx"),
        NewsItem(title="金相場が上昇", summary="商品", url="https://example.test/gold"),
        NewsItem(title="ビットコイン市場", summary="暗号資産", url="https://example.test/btc"),
    ]


def _collector(tmp_path: Path, provider) -> NewsCollector:
    step = NewsCollector(
        run_id="run-1",
        run_dir=tmp_path,
        providers=[provider],
        final_count=3,
    )
    step._build_selection_prompt = lambda candidates, recent: "candidate selection prompt"  # type: ignore[method-assign]
    return step


def test_llm_selects_only_existing_candidates(tmp_path: Path) -> None:
    items = _items()
    step = _collector(tmp_path, FakeSelectorProvider())

    selected, record = step.select_news(items, ["前回は日経平均株価"])

    assert [item.url for item in selected] == [
        "https://example.test/fx",
        "https://example.test/gold",
        "https://example.test/btc",
    ]
    assert record["mode"] == "llm"
    assert len(record["selections"]) == 3
    assert all(entry in record["candidates"] for entry in record["selected_news"])


def test_unavailable_llm_uses_entity_aware_fallback(tmp_path: Path) -> None:
    items = _items()
    step = _collector(tmp_path, FakeUnavailableSelector())

    selected, record = step.select_news(items, ["前回は日経平均"])

    assert len(selected) == 3
    assert items[0] not in selected
    assert record["mode"] == "fallback"


def test_nikkei_average_name_variants_share_entity_key(tmp_path: Path) -> None:
    step = _collector(tmp_path, FakeUnavailableSelector())

    assert step._extract_entities("日経平均") == step._extract_entities("日経平均株価")


def test_selection_parser_rejects_duplicate_and_out_of_range_indexes(tmp_path: Path) -> None:
    step = _collector(tmp_path, FakeUnavailableSelector())
    raw = (
        '{"selections": ['
        '{"index": 1, "reason": "ok"}, '
        '{"index": 1, "reason": "duplicate"}, '
        '{"index": 99, "reason": "invalid"}, '
        '{"index": 2, "reason": "ok2"}'
        ']}'
    )

    assert step._parse_selection(raw, candidate_count=4) == [
        {"index": 1, "reason": "ok"},
        {"index": 2, "reason": "ok2"},
    ]
