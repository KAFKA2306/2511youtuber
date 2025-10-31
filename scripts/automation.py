#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path

from src.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def absolute(path: str | None) -> Path:
    if path is None:
        return ROOT
    value = Path(path)
    if value.is_absolute():
        return value
    return ROOT / value


def log_path(base: str, override: str | None, name: str) -> Path:
    if override:
        return absolute(override)
    directory = absolute(base)
    return directory / f"{name}.log"


def merge_env(values: dict[str, str]) -> dict[str, str]:
    data = os.environ.copy()
    for key, value in values.items():
        if value is not None:
            data[key] = value
    return data


def service_command(activate: str | None, cwd: str | None, command: list[str]) -> list[str]:
    parts: list[str] = []
    if activate:
        parts.append(f". {shlex.quote(str(absolute(activate)))}")
    target = shlex.quote(str(absolute(cwd)))
    parts.append(f"cd {target}")
    parts.append(shlex.join(command))
    return ["bash", "-lc", " && ".join(parts)]


def start_services(automation) -> None:
    for service in automation.services:
        if not service.enabled:
            continue
        command = service_command(automation.venv_activate, service.cwd, service.command)
        env = merge_env(service.env)
        path = log_path(automation.log_dir, service.log_file, service.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as stream:
            if service.background:
                subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, env=env, cwd=ROOT, start_new_session=True)
            else:
                subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, env=env, cwd=ROOT, check=True)


def schedule_line(automation, schedule) -> str:
    parts: list[str] = []
    if automation.venv_activate:
        parts.append(f". {shlex.quote(str(absolute(automation.venv_activate)))}")
    parts.append(f"cd {shlex.quote(str(absolute(schedule.cwd)))}")
    env_map = {key: value for key, value in schedule.env.items() if value is not None}
    command = shlex.join(schedule.command)
    if env_map:
        exports = " ".join(f"{key}={shlex.quote(value)}" for key, value in env_map.items())
        command = f"{exports} {command}"
    parts.append(command)
    path = log_path(automation.log_dir, schedule.log_file, schedule.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"{schedule.cron} {' && '.join(parts)} >> {shlex.quote(str(path))} 2>&1"


def build_schedule(automation) -> list[str]:
    lines: list[str] = []
    for schedule in automation.schedules:
        if not schedule.enabled:
            continue
        lines.append(schedule_line(automation, schedule))
    return lines


def apply_cron(lines: list[str]) -> None:
    if not lines:
        return
    content = "\n".join(lines) + "\n"
    subprocess.run(["crontab", "-"], input=content, text=True, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-services", action="store_true")
    parser.add_argument("--skip-cron", action="store_true")
    parser.add_argument("--install-cron", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config.load()
    automation = config.automation
    if not automation.enabled:
        return
    if not args.skip_services:
        start_services(automation)
    if args.skip_cron:
        return
    lines = build_schedule(automation)
    if args.install_cron:
        apply_cron(lines)
    else:
        for line in lines:
            print(line)


if __name__ == "__main__":
    main()
