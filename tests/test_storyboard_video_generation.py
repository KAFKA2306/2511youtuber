import pytest
from pydantic import ValidationError

from src.providers.video_generation import MiniMaxH3Provider, StoryboardPromptCompiler
from src.storyboard import ReferenceAsset, Shot, TypographyCue, VideoStoryboard


def make_storyboard(**overrides):
    shots = [
        Shot(
            shot_id=f"s{i + 1:02d}",
            start_sec=i * 2.4,
            end_sec=(i + 1) * 2.4,
            message=f"message {i + 1}",
            composition="wide financial explainer",
            motion=["slow push"],
            typography=[TypographyCue(text=f"label {i + 1}", reveal="stage-1")],
        )
        for i in range(5)
    ]
    data = {
        "storyboard_id": "fixture-12s",
        "duration_seconds": 12,
        "aspect_ratio": "16:9",
        "resolution_target": "768P",
        "global_style": "clean flat-vector news explainer",
        "shots": shots,
        "source_evidence_ids": ["evidence-1"],
        "gap_policy": "forbid",
    }
    data.update(overrides)
    return VideoStoryboard(**data)


def test_12_second_five_shot_fixture_compiles_deterministically():
    storyboard = make_storyboard()
    compiler = StoryboardPromptCompiler()
    first = compiler.compile(storyboard)
    second = compiler.compile(storyboard)
    assert first == second
    assert first.count("message=") == 5

    request = MiniMaxH3Provider(api_key="test").compile_request(storyboard)
    assert request["model"] == "MiniMax-H3"
    assert request["duration"] == 12
    assert request["resolution"] == "768P"
    assert request["ratio"] == "16:9"
    assert request["content"][0]["type"] == "text"


def test_overlap_fails_closed():
    with pytest.raises(ValidationError, match="overlaps"):
        make_storyboard(
            shots=[
                Shot(shot_id="s1", start_sec=0, end_sec=5, message="one"),
                Shot(shot_id="s2", start_sec=4, end_sec=8, message="two"),
            ],
            gap_policy="allow",
        )


def test_gap_policy_forbid_fails_closed():
    with pytest.raises(ValidationError, match="gap"):
        make_storyboard(
            shots=[
                Shot(shot_id="s1", start_sec=0, end_sec=4, message="one"),
                Shot(shot_id="s2", start_sec=5, end_sec=12, message="two"),
            ]
        )


def test_duration_overflow_fails_closed():
    with pytest.raises(ValidationError, match="exceeds storyboard duration"):
        make_storyboard(
            shots=[Shot(shot_id="s1", start_sec=0, end_sec=13, message="one")],
            gap_policy="allow",
        )


def test_one_shot_one_message_lint_rejects_multiline_message():
    with pytest.raises(ValidationError, match="one-shot-one-message"):
        Shot(shot_id="s1", start_sec=0, end_sec=1, message="first\nsecond")


def test_unknown_reference_asset_fails_closed():
    with pytest.raises(ValidationError, match="unknown assets"):
        make_storyboard(
            shots=[
                Shot(
                    shot_id="s1",
                    start_sec=0,
                    end_sec=12,
                    message="one",
                    reference_asset_ids=["missing"],
                )
            ]
        )


def test_minimax_reference_limits_and_mode_mixing():
    first = ReferenceAsset(
        asset_id="first",
        kind="image",
        uri="https://example.invalid/first.png",
        role="first_frame",
    )
    ref = ReferenceAsset(
        asset_id="ref",
        kind="image",
        uri="https://example.invalid/ref.png",
        role="reference_image",
    )
    storyboard = make_storyboard(reference_assets=[first, ref])
    with pytest.raises(ValueError, match="cannot be mixed"):
        MiniMaxH3Provider(api_key="test").compile_request(storyboard)


def test_minimax_reference_content_matches_v2_nested_url_contract():
    ref = ReferenceAsset(
        asset_id="character",
        kind="image",
        uri="https://example.invalid/character.png",
        role="reference_image",
    )
    request = MiniMaxH3Provider(api_key="test").compile_request(
        make_storyboard(reference_assets=[ref])
    )
    assert request["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "https://example.invalid/character.png"},
        "role": "reference_image",
    }


def test_minimax_total_reference_media_duration_fails_closed():
    video = ReferenceAsset(
        asset_id="motion",
        kind="video",
        uri="https://example.invalid/motion.mp4",
        role="reference_video",
        duration_seconds=10,
    )
    audio = ReferenceAsset(
        asset_id="sound",
        kind="audio",
        uri="https://example.invalid/sound.mp3",
        role="reference_audio",
        duration_seconds=6,
    )
    with pytest.raises(ValueError, match="total reference video/audio duration"):
        MiniMaxH3Provider(api_key="test").compile_request(
            make_storyboard(reference_assets=[video, audio])
        )


def test_minimax_text_only_adaptive_ratio_fails_closed():
    with pytest.raises(ValueError, match="concrete aspect ratio"):
        MiniMaxH3Provider(api_key="test").compile_request(
            make_storyboard(aspect_ratio="adaptive")
        )


def test_minimax_provider_does_not_require_network_for_compile():
    storyboard = make_storyboard()
    provider = MiniMaxH3Provider(api_key="")
    request = provider.compile_request(storyboard)
    assert request["duration"] == 12
    with pytest.raises(RuntimeError, match="MINIMAX_API_KEY"):
        provider.create_task(storyboard)
