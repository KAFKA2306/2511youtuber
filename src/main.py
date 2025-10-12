import argparse
import sys

from apps.youtube import run as run_youtube


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--news-query")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_youtube(news_query=args.news_query)


if __name__ == "__main__":
    sys.exit(main())
