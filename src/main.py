import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from apps.youtube import run as run_youtube


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--news-query")
    return parser.parse_args()


def main() -> int:
    env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    args = parse_args()
    return run_youtube(news_query=args.news_query)


if __name__ == "__main__":
    sys.exit(main())
