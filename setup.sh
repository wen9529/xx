#!/bin/bash

# StreamForge Termux Setup Script (Ultimate Fix)

echo "🚀 开始安装/修复依赖环境..."

# 1. 基础工具安装
pkg update -y 
# file 命令用于检查二进制文件类型
pkg install -y python ffmpeg git nodejs wget aria2 alist vim procps jq file

# 2. Python 依赖
pip install python-telegram-bot requests python-dotenv

# 3. 安装 PM2
if ! command -v pm2 &> /dev/null; then
    npm install pm2 -g
fi

# 4. Cloudflared 环境检查 (修复架构问题)
pkill -f cloudflared || true

# 架构检测
ARCH=$(uname -m)
CF_URL=""
echo "🔍 检测到系统架构: $ARCH"

case $ARCH in
    aarch64)
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64"
        ;;
    x86_64)
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        ;;
    arm*)
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
        ;;
    *)
        echo "⚠️ 未知架构，尝试下载 Android ARM64 版本..."
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64"
        ;;
esac

install_cloudflared() {
    if [ -f "cloudflared" ]; then
        # 检查是否为有效的 ELF 二进制文件
        if file cloudflared | grep -q "ELF"; then
            echo "✅ Cloudflared 已存在且格式正确。"
            return
        else
            echo "⚠️ Cloudflared 文件损坏 (可能是 HTML 页面)，重新下载..."
            rm cloudflared
        fi
    fi

    echo "⬇️ 下载 Cloudflared ($ARCH)..."
    echo "🔗 源: $CF_URL"
    curl -L "$CF_URL" -o cloudflared
    chmod +x cloudflared
    
    # 二次检查
    if ! file cloudflared | grep -q "ELF"; then
        echo "❌ 下载失败！下载的文件不是二进制程序。请检查网络或手动下载。"
        # 尝试备用源 (Cloudflare 官方)
        echo "🔄 尝试备用下载源..."
        curl -L "https://github.com/cloudflare/cloudflared/releases/download/2024.4.1/cloudflared-linux-android-arm64" -o cloudflared
        chmod +x cloudflared
    fi
}

install_cloudflared

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

# 7. 启动 Alist 并初始化 (关键修复)
echo "🔐 配置 Alist..."
export ALIST_DATA_DIR="./alist_data"
mkdir -p "$ALIST_DATA_DIR"

pm2 delete all >/dev/null 2>&1
pkill -f "alist server" || true

echo "⏳ 启动 Alist 服务 (请等待 15秒)..."
nohup alist server --data "$ALIST_DATA_DIR" > alist_init.log 2>&1 &
ALIST_PID=$!

sleep 15

if ! ps -p $ALIST_PID > /dev/null; then
    echo "❌ Alist 启动失败，日志:"
    cat alist_init.log
else
    # 设置密码
    echo "⚙️ 设置管理员密码..."
    alist admin set "${ALIST_PASSWORD:-admin}" --data "$ALIST_DATA_DIR"
    
    # --- 自动化挂载本地存储 ---
    echo "💾 正在自动初始化 Alist 存储..."
    # 使用 Python 脚本调用 API 初始化存储，解决 'storage not found'
    python3 -c "
import sys, os
sys.path.append(os.getcwd())
try:
    from modules.alist import init_default_storage
    if init_default_storage():
        print('✅ [Success] 本地存储已自动挂载到 /')
    else:
        print('⚠️ [Skip] 存储初始化跳过或失败 (可能已存在)')
except Exception as e:
    print(f'❌ [Error] 初始化存储脚本出错: {e}')
"
    # -----------------------
    
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

echo "✅ 系统安装修复完成！"
echo "👉 请向 Bot 发送 /start"
