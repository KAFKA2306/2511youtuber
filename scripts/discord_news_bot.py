import os
import subprocess
from pathlib import Path
from typing import Any

import discord
from discord import app_commands

from src.utils.discord_config import load_discord_config, resolve_path


def load_environment(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def workflow_command(settings: dict[str, Any], query: str) -> list[str]:
    command = list(settings["workflow_command"])
    command.extend([settings["workflow_argument_flag"], query])
    return command


def register_news_command(tree: app_commands.CommandTree, settings: dict[str, Any], project_root: Path) -> None:
    response_template = settings["response_template"]
    starter_template = settings["starter_template"]
    thread_prefix = settings["thread_prefix"]
    thread_name_limit = int(settings["thread_name_limit"])
    thread_message = settings["thread_message"]
    command = settings["command_name"]
    description = settings["command_description"]

    @tree.command(name=command, description=description)
    async def handle(interaction: discord.Interaction, query: str) -> None:
        await interaction.response.send_message(response_template.format(query=query), ephemeral=True)
        starter = await interaction.channel.send(starter_template.format(query=query))
        thread_name = f"{thread_prefix}{query[:thread_name_limit]}"
        thread = await starter.create_thread(name=thread_name)
        await thread.send(thread_message)
        subprocess.Popen(workflow_command(settings, query), cwd=str(project_root))


def create_client(settings: dict[str, Any], project_root: Path) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True

    class Client(discord.Client):
        def __init__(self) -> None:
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)

        async def setup_hook(self) -> None:
            register_news_command(self.tree, settings, project_root)
            await self.tree.sync()

    return Client()


def main() -> None:
    config = load_discord_config()
    news_settings: dict[str, Any] = config["news_bot"]
    project_root = resolve_path(".")
    load_environment(resolve_path(news_settings["environment_file"]))
    token = os.environ[news_settings["token_env"]]
    client = create_client(news_settings, project_root)
    client.run(token)


if __name__ == "__main__":
    main()
