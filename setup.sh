#!/bin/bash

# StreamForge Termux Setup Script

echo "🚀 开始安装/修复依赖环境..."

# 1. 基础工具安装
pkg update -y 
pkg install -y python ffmpeg git nodejs wget aria2

# 2. Python 依赖
echo "🐍 安装/更新 Python 库..."
pip install python-telegram-bot requests python-dotenv

# 3. 安装 PM2 (如果未安装)
if ! command -v pm2 &> /dev/null; then
    echo "📦 安装 PM2..."
    npm install pm2 -g
fi

# 4. Cloudflared
echo "☁️ 检查 Cloudflared..."
if [ ! -f "cloudflared" ]; then
    echo "下载 cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -O cloudflared
    chmod +x cloudflared
else
    echo "✅ Cloudflared 已存在"
fi

# 5. 配置 Aria2
echo "⚙️ 配置 Aria2..."
if [ ! -f "aria2.session" ]; then
    touch aria2.session
fi

if [ ! -f "aria2.conf" ]; then
    cat <<EOF > aria2.conf
# 开启 RPC
enable-rpc=true
# 允许所有来源
rpc-allow-origin-all=true
# 允许非外部访问
rpc-listen-all=false
# RPC 端口
rpc-listen-port=6800
# RPC 密钥 (留空则无密码，方便 Termux 本地使用)
# rpc-secret=你的密码
# 文件保存路径 (默认当前目录下的 downloads)
dir=${HOME}/downloads
# 断点续传
continue=true
# 进度保存
input-file=$(pwd)/aria2.session
save-session=$(pwd)/aria2.session
save-session-interval=60
EOF
    echo "✅ aria2.conf 已创建"
fi

# 6. 配置 .env
echo "📝 检查环境变量..."
CONFIG_PATH=""

if [ -f "../.env" ]; then
    echo "✅ 在上级目录找到 .env，将使用该配置。"
    CONFIG_PATH="../.env"
elif [ -f ".env" ]; then
    echo "✅ 在当前目录找到 .env。"
    CONFIG_PATH=".env"
else
    echo "⚠️ 未找到配置文件，开始创建..."
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
    echo "✅ .env 创建完成"
fi

# 7. 生成 PM2 Ecosystem 配置 (使用 JSON 格式以兼容所有环境)
echo "🤖 生成进程管理配置 (ecosystem.config.json)..."

# 清理旧的配置文件，避免冲突
rm -f ecosystem.config.js ecosystem.config.cjs

cat <<EOF > ecosystem.config.json
{
  "apps": [
    {
      "name": "alist",
      "script": "alist",
      "args": "server",
      "interpreter": "none",
      "autorestart": true
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
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    },
    {
      "name": "watcher",
      "script": "watcher.py",
      "interpreter": "python",
      "autorestart": true,
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  ]
}
EOF

echo "🎉 安装修复完成！"
echo "------------------------------------------------"
echo "请执行以下命令重启所有服务以加载自动更新模块："
echo "pm2 delete all                     # 1. 清理旧进程"
echo "pm2 start ecosystem.config.json    # 2. 启动新配置 (包含 watcher)"
echo "pm2 save                           # 3. 保存开机自启"
echo "pm2 logs watcher                   # 4. 查看自动更新日志"
echo "------------------------------------------------"
echo "⚠️  重要提示：请确保在 Alist 后台 -> 设置 -> 其他 -> Aria2 中配置："
echo "   Aria2 地址: http://127.0.0.1:6800/jsonrpc"
echo "   Aria2 密钥: (留空)"
echo "------------------------------------------------"
