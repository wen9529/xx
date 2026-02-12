#!/bin/bash

# StreamForge Termux Setup Script

echo "🚀 开始安装依赖环境..."

# 1. 更新包管理器并安装基础工具
# 新增 aria2，因为 Alist 离线下载通常需要它
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg git nodejs wget aria2

# 2. 安装 Python 依赖
echo "🐍 安装 Python 库..."
pip install python-telegram-bot requests python-dotenv

# 3. 安装 Cloudflared (用于内网穿透)
echo "☁️ 正在安装 Cloudflared (用于远程访问)..."
if [ ! -f "cloudflared" ]; then
    echo "下载 cloudflared-linux-android-arm64..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -O cloudflared
    chmod +x cloudflared
    echo "✅ Cloudflared 下载完成"
else
    echo "✅ Cloudflared 已存在"
fi

# 4. 配置 .env
echo "📝 配置环境变量..."
CONFIG_NEEDED=true

if [ -f ".env" ]; then
    echo "⚠️ 检测到现有的 .env 配置文件。"
    read -p "❓ 是否重新输入配置信息 (Bot Token 等)? (y/n, 默认 n): " RECONFIG
    if [[ "$RECONFIG" != "y" ]]; then
        CONFIG_NEEDED=false
        echo "✅ 跳过配置，使用现有 .env 文件。"
    else
        echo "🔄 开始重新配置..."
    fi
fi

if [ "$CONFIG_NEEDED" = true ]; then
    read -p "请输入 Telegram Bot Token: " TG_BOT_TOKEN
    read -p "请输入你的 Telegram ID (Admin ID): " TG_ADMIN_ID
    read -p "请输入 GitHub 用户名 (Owner): " GITHUB_OWNER
    read -p "请输入 GitHub 仓库名 (Repo): " GITHUB_REPO
    read -p "请输入 GitHub PAT (Token): " GITHUB_PAT
    read -p "请输入默认 RTMP 推流地址 (可选): " RTMP_URL
    echo "提示: 公网地址可在 Bot 中动态生成，此处可留空。"
    read -p "请输入 Alist 公网地址 (留空则使用动态隧道): " ALIST_PUBLIC_URL
    
    cat <<EOF > .env
TG_BOT_TOKEN=$TG_BOT_TOKEN
TG_ADMIN_ID=$TG_ADMIN_ID
GITHUB_OWNER=$GITHUB_OWNER
GITHUB_REPO=$GITHUB_REPO
GITHUB_PAT=$GITHUB_PAT
RTMP_URL=$RTMP_URL
ALIST_HOST=http://127.0.0.1:5244
ALIST_PUBLIC_URL=$ALIST_PUBLIC_URL
ALIST_USER=admin
ALIST_PASSWORD=admin
EOF
    echo "✅ .env 文件已更新！"
fi

echo "🎉 安装完成！"
echo "请确保 Alist 已经在后台运行 (alist server) 且已安装 aria2 (pkg install aria2)。"
echo "运行机器人: python bot.py"
