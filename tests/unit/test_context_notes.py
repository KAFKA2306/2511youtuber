import json

from src.models import ScriptContextNotes, sanitize_context_note
from src.utils.history import extract_script_notes, load_previous_context


def test_known_placeholder_notes_are_discarded():
    notes = ScriptContextNotes.from_mapping(
        {
            "recent_topics_note": "金融ニュース速報：日本経済の最新動向",
            "next_theme_note": "市場は急激な変動を見せています。",
        }
    )

    assert notes.is_empty()


def test_real_context_note_is_preserved_verbatim():
    note = "日銀は政策金利を据え置き、国債買い入れ方針を維持"

    assert sanitize_context_note(note) == note


def test_history_skips_placeholder_run_and_uses_next_real_run(tmp_path):
    placeholder_run = tmp_path / "20260102_000000"
    placeholder_run.mkdir()
    (placeholder_run / "script.json").write_text(
        json.dumps(
            {
                "recent_topics_note": "金融ニュース速報：日本経済の最新動向",
                "next_theme_note": "市場は急激な変動を見せています",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (placeholder_run / "metadata.json").write_text(
        json.dumps({"title": "金融ニュース速報：日本経済の最新動向"}, ensure_ascii=False),
        encoding="utf-8",
    )

    real_run = tmp_path / "20260101_000000"
    real_run.mkdir()
    (real_run / "script.json").write_text("{}", encoding="utf-8")
    (real_run / "metadata.json").write_text(
        json.dumps({"title": "米国雇用統計と金利見通し"}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert extract_script_notes(placeholder_run).is_empty()
    notes = load_previous_context(tmp_path, "20260103_000000")
    assert notes.recent_topics_note == "米国雇用統計と金利見通し"
    assert notes.next_theme_note == ""
