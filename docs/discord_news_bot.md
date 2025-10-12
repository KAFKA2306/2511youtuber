# Discord News Bot Operations

## Prerequisites
- `config/.env` contains `DISCORD_BOT_TOKEN`
- Dependencies are installed via `uv sync`

## Manual launch
Run `./scripts/run_discord_news_bot.sh` from the project root. The helper script loads `config/.env`, prefers `uv`, and falls back to the system `python`.

## Cron `@reboot`
Add to the desired user crontab:

```
@reboot /bin/bash /home/kafka/projects/2510youtuber/youtube-ai-v2/scripts/run_discord_news_bot.sh >> /var/log/discord_news_bot.log 2>&1
```

Cron restarts the bot after every reboot. Adjust the log location to match available write privileges.

## Systemd unit
Place the following at `/etc/systemd/system/discord-news-bot.service` (requires root):

```
[Unit]
Description=Discord News Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/kafka/projects/2510youtuber/youtube-ai-v2
ExecStart=/home/kafka/projects/2510youtuber/youtube-ai-v2/scripts/run_discord_news_bot.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then run:

```
sudo systemctl daemon-reload
sudo systemctl enable --now discord-news-bot
sudo systemctl status discord-news-bot
```

Systemd keeps the process online, restarts it on failure, and starts it automatically after reboots. Stop it with `sudo systemctl stop discord-news-bot` when you need to update dependencies or tokens.
