import json

from src.providers.llm import load_prompt_template
from src.providers.tts import VOICEVOXProvider
from src.steps.script import ScriptGenerator


def test_script_generation_prompt_includes_strict_voice_contract():
    prompt = load_prompt_template("script_generation")
    assert "[VOICE: key=value, key=value]" in prompt
    assert "speed" in prompt
    assert "pitch" in prompt
    assert "intonation" in prompt
    assert "未知キーは禁止" in prompt
    assert "最大1個" in prompt
    assert "タグだけのセリフは禁止" in prompt


def test_non_script_prompt_does_not_receive_voice_contract():
    prompt = load_prompt_template("news_collection")
    assert "[VOICE: key=value, key=value]" not in prompt


def test_generated_fixture_parses_then_voicevox_consumes_directive():
    raw = json.dumps(
        {
            "segments": [
                {
                    "speaker": "春日部つむぎ",
                    "text": "利益率が改善したよ [VOICE: speed=1.1, pitch=0.05, intonation=1.4]",
                }
            ]
        },
        ensure_ascii=False,
    )
    generator = ScriptGenerator.__new__(ScriptGenerator)
    script = generator._parse_and_validate(raw)
    cleaned, overrides = VOICEVOXProvider._parse_voice_directive(script.segments[0].text)
    assert cleaned == "利益率が改善したよ"
    assert overrides == {
        "speedScale": 1.1,
        "pitchScale": 0.05,
        "intonationScale": 1.4,
    }
