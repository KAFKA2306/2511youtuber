import os
import subprocess
from pathlib import Path

import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True


class NewsClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = NewsClient()
project_path = Path(__file__).resolve().parents[1]
env_path = project_path / "config" / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    os.environ.setdefault(key.strip(), value.strip())

@client.tree.command(name="news", description="任意のニュースクエリを投入")
async def news(interaction: discord.Interaction, query: str):
    await interaction.response.send_message(f"📰 調査開始: `{query}`", ephemeral=True)
    channel = interaction.channel
    starter = await channel.send(f"🧭 {query}")
    thread = await starter.create_thread(name=f"ニュース調査: {query[:40]}")
    await thread.send("ワークフローを実行します")
    subprocess.Popen(["uv", "run", "python", "-m", "src.main", "--news-query", query], cwd=str(project_path))

client.run(os.getenv("DISCORD_BOT_TOKEN"))
