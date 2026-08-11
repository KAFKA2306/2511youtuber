import pytest

from src.providers.tts import VOICEVOXProvider


@pytest.fixture(autouse=True)
def slow_down_tests():
    """Override the repository-wide API delay for these pure unit tests."""
    yield


def test_parse_voice_directive_strips_tag_and_maps_fields():
    text, params = VOICEVOXProvider._parse_voice_directive(
        "営業利益率を確認します [VOICE: speed=1.2, pitch=-0.05, intonation=1.5]"
    )

    assert text == "営業利益率を確認します"
    assert params == {
        "speedScale": 1.2,
        "pitchScale": -0.05,
        "intonationScale": 1.5,
    }


def test_parse_voice_directive_allows_partial_reordered_fields():
    text, params = VOICEVOXProvider._parse_voice_directive(
        "確認なのだ？ [voice: intonation=1.4, speed=0.9]"
    )

    assert text == "確認なのだ？"
    assert params == {"intonationScale": 1.4, "speedScale": 0.9}


def test_parse_voice_directive_without_tag_is_unchanged():
    text, params = VOICEVOXProvider._parse_voice_directive("通常のセリフ")
    assert text == "通常のセリフ"
    assert params == {}


@pytest.mark.parametrize(
    "text",
    [
        "本文 [VOICE:]",
        "本文 [VOICE: volume=2]",
        "本文 [VOICE: speed=fast]",
        "本文 [VOICE: speed=nan]",
        "本文 [VOICE: speed=1.0, speed=1.1]",
        "本文 [VOICE: speed=1.0] [VOICE: pitch=0.1]",
        "[VOICE: speed=1.0]",
    ],
)
def test_parse_voice_directive_rejects_malformed_controls(text):
    with pytest.raises(ValueError):
        VOICEVOXProvider._parse_voice_directive(text)


def test_execute_passes_clean_text_and_overrides_to_synth(monkeypatch):
    provider = VOICEVOXProvider("http://127.0.0.1:50021", {"つむぎ": 8})
    captured = {}
    sentinel = object()

    def fake_synth(text, speaker, **kwargs):
        captured.update(text=text, speaker=speaker, kwargs=kwargs)
        return sentinel

    monkeypatch.setattr(provider, "_synth", fake_synth)

    result = provider.execute(
        "落ち着いて確認します [VOICE: speed=0.8, pitch=-0.05, intonation=0.7]",
        "つむぎ",
    )

    assert result is sentinel
    assert captured["text"] == "落ち着いて確認します"
    assert captured["speaker"] == "つむぎ"
    assert captured["kwargs"]["voice_overrides"] == {
        "speedScale": 0.8,
        "pitchScale": -0.05,
        "intonationScale": 0.7,
    }
