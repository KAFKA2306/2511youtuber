# Automation Playbook

## 必要なタスク
- Gemini, Perplexity, Voicevox などの API トークンを `config/.env` に設定する。
- `config/default.yaml` の `automation` と `steps` セクションを目的に合わせて調整する。
- Run 用フォルダ (`runs/`) とログフォルダ (`logs/automation/`) の書き込み権限を確認する。
- Docker が利用できる環境であれば Voicevox 用のコンテナ実行を許可する。

## セットアップ手順
1. 依存関係導入: `uv sync`
2. 環境変数テンプレート複製: `cp config/.env.example config/.env`
3. 必要なシークレットを `config/.env` に記入する。
4. `config/default.yaml` で必要なステップやプロバイダー、`automation.services` と `automation.schedules` を編集する。
5. 仮想環境を有効化: `source .venv/bin/activate`

## セットアップコマンド
```bash
uv sync
cp config/.env.example config/.env
source .venv/bin/activate
nohup bash scripts/start_aim.sh >/dev/null 2>&1 &
nohup bash scripts/voicevox_manager.sh start >/dev/null 2>&1 &
nohup uv run python scripts/discord_news_bot.py >/dev/null 2>&1 &
```

## 主要コマンド (sudo 利用)
```bash
# パッケージ導入
sudo apt-get install -y docker.io ffmpeg

# Docker デーモン起動・自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# Cron サービス制御
sudo systemctl restart cron
sudo systemctl status cron

# Cron 設定確認・削除 (root crontab)
sudo crontab -l
sudo crontab -r

# Aim ダッシュボード (昇格が必要な環境向け)
sudo nohup bash scripts/start_aim.sh >/dev/null 2>&1 &

# Voicevox コンテナ強制停止
sudo docker rm -f voicevox-nemo

# Automation Runner を root で実行
sudo /home/kafka/2511youtuber/.venv/bin/python scripts/automation.py --skip-cron
```

## 実行手順
```bash
# 手動実行
python -m src.main --news-query "任意のクエリ"

# サービス起動のみ
python scripts/automation.py --skip-cron

# Cron 行の確認
python scripts/automation.py --skip-services

# Cron 設定適用
python scripts/automation.py --install-cron

# ログ確認例
tail -f logs/automation/workflow_minutely.log

# Cron スクリプト直接実行
bash scripts/run_workflow_cron.sh

# Cron 設定確認
crontab -l

# Cron 削除
crontab -r
```

## サービス操作コマンド
```bash
# Aim ダッシュボード起動
nohup bash scripts/start_aim.sh >/dev/null 2>&1 &

# Voicevox 管理
bash scripts/voicevox_manager.sh start
bash scripts/voicevox_manager.sh stop
bash scripts/voicevox_manager.sh restart
bash scripts/voicevox_manager.sh status
bash scripts/voicevox_manager.sh logs
bash scripts/voicevox_manager.sh test

# Discord Bot 単体起動
uv run python scripts/discord_news_bot.py

# Automation Runner 再実行
python scripts/automation.py --skip-cron

# 生成物ディレクトリ確認
ls runs/

# Automation ログ一覧
ls logs/automation
```

## 運用のポイント
- Discord Bot, Voicevox, Aim UI の起動は `automation.services` で制御する。サービス単位で `enabled: false` を設定すれば停止できる。
- スケジュールの周期変更は `automation.schedules` の `cron` を編集し `--install-cron` を再実行する。
- `logs/automation/` のサイズが増えたらローテーションまたは削除を実施する。
- `runs/` ディレクトリに生成される実行結果はダッシュボードと後続処理の入力になるため、削除前に必要な成果物をアーカイブする。
