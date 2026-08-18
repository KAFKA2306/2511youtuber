from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

_BRAND_ID_ENV = "YOUTUBER_BRAND_ID"
_BRAND_DISPLAY_NAME_ENV = "YOUTUBER_BRAND_DISPLAY_NAME"
_BRAND_DISCLOSURE_ENV = "YOUTUBER_BRAND_DISCLOSURE_TEXT"
_BRAND_CONFIG_SHA_ENV = "YOUTUBER_BRAND_CONFIG_SHA256"
_BRAND_ENV_NAMES = (
    _BRAND_ID_ENV,
    _BRAND_DISPLAY_NAME_ENV,
    _BRAND_DISCLOSURE_ENV,
    _BRAND_CONFIG_SHA_ENV,
)


class BrandProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    disclosure_text: str = Field(min_length=1)

    def validate_brand_id(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", self.brand_id):
            raise ValueError(
                "brand_id must use lowercase letters, numbers, underscores, or hyphens"
            )


def load_brand_profile(path: str | Path) -> BrandProfile:
    profile_path = Path(path)
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Brand config must be a YAML mapping")
    profile = BrandProfile.model_validate(raw)
    profile.validate_brand_id()
    return profile


def activate_brand_profile(path: str | Path) -> BrandProfile:
    profile_path = Path(path)
    profile = load_brand_profile(profile_path)
    digest = hashlib.sha256(profile_path.read_bytes()).hexdigest()
    os.environ[_BRAND_ID_ENV] = profile.brand_id
    os.environ[_BRAND_DISPLAY_NAME_ENV] = profile.display_name
    os.environ[_BRAND_DISCLOSURE_ENV] = profile.disclosure_text
    os.environ[_BRAND_CONFIG_SHA_ENV] = digest
    return profile


def clear_active_brand() -> None:
    for name in _BRAND_ENV_NAMES:
        os.environ.pop(name, None)


def active_brand() -> dict[str, str] | None:
    brand_id = os.getenv(_BRAND_ID_ENV, "").strip()
    if not brand_id:
        return None
    display_name = os.getenv(_BRAND_DISPLAY_NAME_ENV, "").strip()
    disclosure_text = os.getenv(_BRAND_DISCLOSURE_ENV, "").strip()
    config_sha256 = os.getenv(_BRAND_CONFIG_SHA_ENV, "").strip()
    if not display_name or not disclosure_text or not config_sha256:
        raise ValueError("Active brand profile is incomplete")
    return {
        "brand_id": brand_id,
        "display_name": display_name,
        "disclosure_text": disclosure_text,
        "config_sha256": config_sha256,
    }


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
    disclosure = brand["disclosure_text"]
    if disclosure not in description:
        branded["description"] = f"{description}\n\n{disclosure}".strip()

    branded["brand"] = {
        "brand_id": brand["brand_id"],
        "display_name": brand["display_name"],
        "config_sha256": brand["config_sha256"],
    }
    return branded
