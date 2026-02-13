#!/bin/bash

# StreamForge Termux Setup Script (Safe Update Version)

echo "🚀 开始安装/修复依赖环境..."

# 1. 基础工具安装
pkg update -y 
pkg install -y python ffmpeg git nodejs wget aria2 alist vim procps jq file

# 2. Python 依赖
pip install python-telegram-bot requests python-dotenv

# 3. 安装 PM2
if ! command -v pm2 &> /dev/null; then
    npm install pm2 -g
fi

# 4. Cloudflared 环境检查
pkill -f cloudflared || true
ARCH=$(uname -m)
CF_URL=""
echo "🔍 检测系统架构: $ARCH"

case $ARCH in
    aarch64) CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64" ;;
    x86_64)  CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
    arm*)    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm" ;;
    *)       CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64" ;;
esac

if [ -f "cloudflared" ]; then
    if ! file cloudflared | grep -q "ELF"; then
        echo "⚠️ Cloudflared 文件损坏，重新下载..."
        rm cloudflared
    fi
fi

if [ ! -f "cloudflared" ]; then
    echo "⬇️ 下载 Cloudflared..."
    curl -L "$CF_URL" -o cloudflared
    chmod +x cloudflared
fi

# 5. 配置 Aria2
mkdir -p "${HOME}/downloads"
if [ ! -f "aria2.session" ]; then touch aria2.session; fi
if [ ! -f "aria2.conf" ]; then
    cat <<EOF > aria2.conf
enable-rpc=true
rpc-allow-origin-all=true
rpc-listen-all=false
rpc-listen-port=6800
dir=${HOME}/downloads
continue=true
input-file=$(pwd)/aria2.session
save-session=$(pwd)/aria2.session
save-session-interval=60
EOF
fi

# 6. 配置 .env
CONFIG_PATH=".env"
if [ -f "../.env" ]; then CONFIG_PATH="../.env"; fi

if [ ! -f "$CONFIG_PATH" ]; then
    echo "⚠️ 未找到配置文件，开始向导..."
    read -p "请输入 Telegram Bot Token: " TG_BOT_TOKEN
    read -p "请输入 Admin ID: " TG_ADMIN_ID
    read -p "GitHub Owner: " GITHUB_OWNER
    read -p "GitHub Repo: " GITHUB_REPO
    read -p "GitHub PAT: " GITHUB_PAT
    
    cat <<EOF > .env
TG_BOT_TOKEN=$TG_BOT_TOKEN
TG_ADMIN_ID=$TG_ADMIN_ID
GITHUB_OWNER=$GITHUB_OWNER
GITHUB_REPO=$GITHUB_REPO
GITHUB_PAT=$GITHUB_PAT
RTMP_URL=
ALIST_HOST=http://127.0.0.1:5244
ALIST_USER=admin
ALIST_PASSWORD=admin
EOF
fi
if [ -f "$CONFIG_PATH" ]; then export $(grep -v '^#' "$CONFIG_PATH" | xargs); fi

# 7. 启动 Alist 并初始化
echo "🔐 配置 Alist..."
export ALIST_DATA_DIR="./alist_data"
mkdir -p "$ALIST_DATA_DIR"

# 关键修改：不要使用 pm2 delete all，这会杀死正在运行更新的 Bot
# 只停止 alist 进行维护
pm2 stop alist >/dev/null 2>&1 || true
pkill -f "alist server" || true

echo "⏳ 启动临时 Alist (请等待 10秒)..."
nohup alist server --data "$ALIST_DATA_DIR" > alist_init.log 2>&1 &
ALIST_PID=$!

sleep 10

if ! ps -p $ALIST_PID > /dev/null; then
    echo "❌ Alist 启动失败，日志:"
    cat alist_init.log
else
    # 设置密码
    alist admin set "${ALIST_PASSWORD:-admin}" --data "$ALIST_DATA_DIR" >/dev/null 2>&1
    
    # 自动化挂载本地存储
    echo "💾 检查并初始化存储..."
    python3 -c "
import sys, os
sys.path.append(os.getcwd())
try:
    from modules.alist import init_default_storage
    init_default_storage()
except Exception as e:
    print(f'⚠️ 存储初始化跳过: {e}')
"
    kill $ALIST_PID 2>/dev/null
fi

# 8. 生成/更新 PM2 配置
cat <<EOF > ecosystem.config.json
{
  "apps": [
    {
      "name": "alist",
      "script": "alist",
      "args": "server",
      "interpreter": "none",
      "autorestart": true,
      "env": { "ALIST_DATA_DIR": "./alist_data" }
    },
    {
      "name": "aria2",
      "script": "aria2c",
      "args": "--conf-path=./aria2.conf",
      "interpreter": "none",
      "autorestart": true
    },
    {
      "name": "stream-bot",
      "script": "bot.py",
      "interpreter": "python",
      "autorestart": true,
      "env": { "PYTHONUNBUFFERED": "1" }
    },
    {
      "name": "watcher",
      "script": "watcher.py",
      "interpreter": "python",
      "autorestart": true,
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  ]
}
EOF

# 9. 启动/重载服务
echo "🔄 更新 PM2 服务状态..."
# 使用 start 来更新配置并启动未运行的服务，已运行的(如Bot)不会被杀死
pm2 start ecosystem.config.json
pm2 save --force

echo "✅ 系统更新/修复完成！"
