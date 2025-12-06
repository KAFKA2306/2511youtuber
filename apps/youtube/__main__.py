#!/usr/bin/env python3
"""Entry point for YouTube CLI when run as a module."""

import argparse
import sys

from apps.youtube import run


def main():
    parser = argparse.ArgumentParser(description="YouTube AI Video Generator")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--news-query", help="Custom news query")

    args = parser.parse_args()

    if args.command == "run":
        exit_code = run(news_query=args.news_query)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
