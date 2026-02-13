#!/bin/bash

# StreamForge Termux Setup Script (Fixed & Polished)

echo "🚀 开始安装/修复依赖环境..."

# 1. 基础工具安装 (新增 jq)
pkg update -y 
pkg install -y python ffmpeg git nodejs wget aria2 alist vim procps jq

# 2. Python 依赖
pip install python-telegram-bot requests python-dotenv

# 3. 安装 PM2
if ! command -v pm2 &> /dev/null; then
    npm install pm2 -g
fi

# 4. Cloudflared 环境检查
pkill -f cloudflared || true
if [ ! -f "cloudflared" ]; then
    echo "⬇️ 下载 cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -o cloudflared
    chmod +x cloudflared
fi

# 5. 配置 Aria2
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

# 加载变量
if [ -f "$CONFIG_PATH" ]; then export $(grep -v '^#' "$CONFIG_PATH" | xargs); fi

# 7. 启动 Alist 并设置密码 (强化版)
echo "🔐 配置 Alist..."
export ALIST_DATA_DIR="./alist_data"
mkdir -p "$ALIST_DATA_DIR"

# 清理旧进程，防止冲突
pm2 delete all >/dev/null 2>&1
pkill -f "alist server" || true

# 启动 Alist
echo "⏳ 正在启动 Alist (请等待 15 秒)..."
nohup alist server --data "$ALIST_DATA_DIR" > alist_init.log 2>&1 &
ALIST_PID=$!

sleep 15

# 检查 Alist 是否存活
if ! ps -p $ALIST_PID > /dev/null; then
    echo "❌ Alist 启动失败，请检查 alist_init.log"
    cat alist_init.log
else
    # 设置密码
    echo "⚙️ 设置管理员密码..."
    alist admin set "${ALIST_PASSWORD:-admin}" --data "$ALIST_DATA_DIR"
    echo "✅ Alist 密码已更新"
    
    # 杀掉临时进程
    kill $ALIST_PID 2>/dev/null
fi

# 8. 生成 PM2 配置
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

# 9. 启动服务
echo "🔄 重启 PM2 服务..."
pm2 start ecosystem.config.json
pm2 save --force

echo "✅ 安装完成！请在 Telegram 向 Bot 发送 /start"
