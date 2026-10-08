from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

_BRAND_ID_ENV = "YOUTUBER_BRAND_ID"
_BRAND_DISPLAY_NAME_ENV = "YOUTUBER_BRAND_DISPLAY_NAME"
_BRAND_DISCLOSURE_ENV = "YOUTUBER_BRAND_DISCLOSURE_TEXT"
_BRAND_CONFIG_SHA_ENV = "YOUTUBER_BRAND_CONFIG_SHA256"
_BRAND_PROFILE_ENV = "YOUTUBER_BRAND_PROFILE_JSON"
_BRAND_APPROVAL_ENV = "YOUTUBER_BRAND_APPROVAL_JSON"
_BRAND_ENV_NAMES = (
    _BRAND_ID_ENV,
    _BRAND_DISPLAY_NAME_ENV,
    _BRAND_DISCLOSURE_ENV,
    _BRAND_CONFIG_SHA_ENV,
    _BRAND_PROFILE_ENV,
    _BRAND_APPROVAL_ENV,
)


class BrandAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    rights_confirmed: bool


class BrandProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    brand_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    disclosure_text: str = Field(min_length=1)
    allowed_topics: list[str] = Field(default_factory=list)
    default_visibility: Literal["private", "unlisted", "public"] = "private"
    intro: BrandAsset | None = None
    outro: BrandAsset | None = None


class BrandApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    brand_id: str = Field(min_length=1)
    brand_config_sha256: str = Field(min_length=64, max_length=64)
    approved: bool
    approved_by: str = Field(min_length=1)
    approved_at: str = Field(min_length=1)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_profile(profile: BrandProfile) -> BrandProfile:
    if profile.schema_version != 1:
        raise ValueError("Unsupported brand profile schema_version")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", profile.brand_id):
        raise ValueError(
            "brand_id must use lowercase letters, numbers, underscores, or hyphens"
        )
    cleaned_topics = [topic.strip() for topic in profile.allowed_topics]
    if any(not topic for topic in cleaned_topics):
        raise ValueError("allowed_topics must not contain empty values")
    for label, asset in (("intro", profile.intro), ("outro", profile.outro)):
        if asset is None:
            continue
        if not asset.rights_confirmed:
            raise ValueError(f"{label} asset must have rights_confirmed=true")
        asset_path = Path(asset.path)
        if asset_path.is_absolute() or ".." in asset_path.parts:
            raise ValueError(f"{label} asset path must be repository-relative")
    return profile


def load_brand_profile(path: str | Path) -> BrandProfile:
    profile_path = Path(path)
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Brand config must be a YAML mapping")
    return _validate_profile(BrandProfile.model_validate(raw))


def load_brand_approval(
    path: str | Path,
    *,
    profile: BrandProfile,
    config_sha256: str,
) -> BrandApproval:
    approval_path = Path(path)
    raw = yaml.safe_load(approval_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Brand approval must be a mapping")
    approval = BrandApproval.model_validate(raw)
    if approval.schema_version != 1:
        raise ValueError("Unsupported brand approval schema_version")
    if approval.approved is not True:
        raise ValueError("Brand approval must explicitly set approved=true")
    if approval.brand_id != profile.brand_id:
        raise ValueError("Brand approval brand_id does not match active brand")
    if approval.brand_config_sha256 != config_sha256:
        raise ValueError("Brand approval does not match the active brand config SHA-256")
    if not re.fullmatch(r"[0-9a-f]{64}", approval.brand_config_sha256):
        raise ValueError("brand_config_sha256 must be a lowercase SHA-256 hex digest")
    try:
        datetime.fromisoformat(approval.approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("approved_at must be an ISO-8601 timestamp") from exc
    return approval


def activate_brand_profile(
    path: str | Path,
    *,
    approval_path: str | Path | None = None,
) -> BrandProfile:
    profile_path = Path(path)
    profile = load_brand_profile(profile_path)
    digest = _sha256(profile_path)
    approval = (
        load_brand_approval(approval_path, profile=profile, config_sha256=digest)
        if approval_path is not None
        else None
    )

    os.environ[_BRAND_ID_ENV] = profile.brand_id
    os.environ[_BRAND_DISPLAY_NAME_ENV] = profile.display_name
    os.environ[_BRAND_DISCLOSURE_ENV] = profile.disclosure_text
    os.environ[_BRAND_CONFIG_SHA_ENV] = digest
    os.environ[_BRAND_PROFILE_ENV] = profile.model_dump_json()
    if approval is not None:
        os.environ[_BRAND_APPROVAL_ENV] = approval.model_dump_json()
    else:
        os.environ.pop(_BRAND_APPROVAL_ENV, None)
    return profile


def clear_active_brand() -> None:
    for name in _BRAND_ENV_NAMES:
        os.environ.pop(name, None)


def active_brand() -> dict[str, Any] | None:
    brand_id = os.getenv(_BRAND_ID_ENV, "").strip()
    if not brand_id:
        return None

    profile_json = os.getenv(_BRAND_PROFILE_ENV, "").strip()
    config_sha256 = os.getenv(_BRAND_CONFIG_SHA_ENV, "").strip()
    if not profile_json or not config_sha256:
        raise ValueError("Active brand profile is incomplete")
    profile = BrandProfile.model_validate(json.loads(profile_json))
    approval_json = os.getenv(_BRAND_APPROVAL_ENV, "").strip()
    approval = (
        BrandApproval.model_validate(json.loads(approval_json))
        if approval_json
        else None
    )

    data = profile.model_dump(mode="json")
    data["config_sha256"] = config_sha256
    data["approved"] = approval is not None and approval.approved is True
    data["approval"] = approval.model_dump(mode="json") if approval else None
    return data


def validate_active_brand_topic(news_query: str | None) -> None:
    brand = active_brand()
    if brand is None:
        return
    allowed_topics = [
        str(topic).strip()
        for topic in brand.get("allowed_topics", [])
        if str(topic).strip()
    ]
    if not allowed_topics:
        return
    query = str(news_query or "").strip()
    if not query:
        raise ValueError(
            "Branded run requires --news-query when allowed_topics is configured"
        )
    folded = query.casefold()
    if not any(topic.casefold() in folded for topic in allowed_topics):
        raise ValueError(
            "Branded run news query is outside allowed_topics: "
            + ", ".join(allowed_topics)
        )


def apply_active_brand_to_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    brand = active_brand()
    if brand is None:
        return dict(metadata)

    branded = dict(metadata)
    title = str(branded.get("title", "")).strip()
    prefix = f"{brand['display_name']} | "
    if title and not title.startswith(prefix):
        branded["title"] = f"{prefix}{title}"

    description = str(branded.get("description", "")).rstrip()
    disclosure = str(brand["disclosure_text"])
    if disclosure not in description:
        branded["description"] = f"{description}\n\n{disclosure}".strip()

    branded["visibility"] = brand["default_visibility"]
    branded["brand"] = {
        "schema_version": brand["schema_version"],
        "brand_id": brand["brand_id"],
        "display_name": brand["display_name"],
        "config_sha256": brand["config_sha256"],
        "intended_visibility": brand["default_visibility"],
    }
    return branded
