import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from apps.youtube import run as run_youtube
from src.brand import activate_brand_profile, clear_active_brand


_EXTERNAL_APPROVAL_ENV = "YOUTUBE_EXTERNAL_PUBLISH_APPROVED"
_PUBLIC_APPROVAL_ENV = "YOUTUBE_PUBLIC_VISIBILITY_APPROVED"
_EXTERNAL_APPROVAL_VALUE = "I_UNDERSTAND_THIS_UPLOADS_EXTERNALLY"
_PUBLIC_APPROVAL_VALUE = "I_UNDERSTAND_THIS_WILL_BE_PUBLIC"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--news-query")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="外部公開せず、生成と投稿準備だけを検証する",
    )
    parser.add_argument(
        "--brand-config",
        type=Path,
        help="顧客別ブランド設定を読み込み、外部公開しないレビュー用runを生成する",
    )
    return parser.parse_args()


def _configure_publication_mode(*, dry_run: bool) -> None:
    """通常実行は公開を許可し、--dry-run時だけ承認を除去する。"""

    if dry_run:
        os.environ.pop(_EXTERNAL_APPROVAL_ENV, None)
        os.environ.pop(_PUBLIC_APPROVAL_ENV, None)
        os.environ["YOUTUBER_FORCE_DRY_RUN"] = "1"
        return

    os.environ[_EXTERNAL_APPROVAL_ENV] = _EXTERNAL_APPROVAL_VALUE
    os.environ[_PUBLIC_APPROVAL_ENV] = _PUBLIC_APPROVAL_VALUE
    os.environ.pop("YOUTUBER_FORCE_DRY_RUN", None)


def main() -> int:
    env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    args = parse_args()
    clear_active_brand()
    if args.brand_config:
        activate_brand_profile(args.brand_config)
    review_only = args.dry_run or args.brand_config is not None
    _configure_publication_mode(dry_run=review_only)
    return run_youtube(news_query=args.news_query, force_dry_run=review_only)


if __name__ == "__main__":
    sys.exit(main())
