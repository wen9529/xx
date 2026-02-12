#!/bin/bash

# StreamForge Termux Setup Script

echo "🚀 开始安装依赖环境..."

# 1. 更新包管理器并安装基础工具
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg git nodejs wget

# 2. 安装 Python 依赖
echo "🐍 安装 Python 库..."
pip install python-telegram-bot requests python-dotenv

# 3. 安装 Cloudflared (用于内网穿透)
echo "☁️ 正在安装 Cloudflared (用于远程访问)..."
# Termux 通常运行在 ARM64 架构上
if [ ! -f "cloudflared" ]; then
    echo "下载 cloudflared-linux-android-arm64..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -O cloudflared
    chmod +x cloudflared
    echo "✅ Cloudflared 下载完成"
else
    echo "✅ Cloudflared 已存在"
fi

# 4. 检查是否需要配置 .env
if [ ! -f ".env" ]; then
    echo "📝 检测到未配置环境，正在创建 .env 文件..."
    
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
    echo "✅ .env 文件已创建！Alist 默认密码为 admin，请在 Alist 中修改后同步更新 .env 文件。"
else
    echo "✅ .env 文件已存在，跳过配置。"
fi

echo "🎉 安装完成！"
echo "请确保 Alist 已经在后台运行 (alist server)。"
echo "运行机器人: python bot.py"
