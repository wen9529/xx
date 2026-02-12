#!/bin/bash

# StreamForge Termux Setup Script

echo "🚀 开始安装/修复依赖环境..."

# 1. 基础工具安装
echo "📦 安装系统软件包..."
pkg update -y 
pkg install -y python ffmpeg git nodejs wget aria2 alist vim procps

# 2. Python 依赖
echo "🐍 安装/更新 Python 库..."
pip install python-telegram-bot requests python-dotenv

# 3. 安装 PM2 (如果未安装)
if ! command -v pm2 &> /dev/null; then
    echo "📦 安装 PM2..."
    npm install pm2 -g
fi

# 4. Cloudflared 环境检查
echo "☁️ 检查 Cloudflared..."
# 杀掉残留进程防止占用
pkill -f cloudflared || true

if [ ! -f "cloudflared" ]; then
    echo "⬇️ 下载 cloudflared (Android arm64)..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -o cloudflared
    chmod +x cloudflared
else
    echo "✅ Cloudflared 已存在"
    chmod +x cloudflared
fi

# 验证 cloudflared 是否可用
if ./cloudflared --version > /dev/null 2>&1; then
    echo "✅ Cloudflared 二进制文件验证通过"
else
    echo "❌ Cloudflared 文件可能损坏，正在重试下载..."
    rm cloudflared
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-arm64 -o cloudflared
    chmod +x cloudflared
fi

# 5. 配置 Aria2
echo "⚙️ 配置 Aria2..."
if [ ! -f "aria2.session" ]; then
    touch aria2.session
fi

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
    echo "✅ aria2.conf 已创建"
fi

# 6. 配置 .env
echo "📝 检查环境变量..."

CONFIG_PATH=".env"
if [ -f "../.env" ]; then
    CONFIG_PATH="../.env"
    echo "✅ 检测到上级目录 .env"
elif [ -f ".env" ]; then
    echo "✅ 检测到当前目录 .env"
else
    echo "⚠️ 未找到配置文件，开始向导..."
    read -p "请输入 Telegram Bot Token: " TG_BOT_TOKEN
    read -p "请输入 Admin ID: " TG_ADMIN_ID
    read -p "GitHub Owner (用户名): " GITHUB_OWNER
    read -p "GitHub Repo (仓库名): " GITHUB_REPO
    read -p "GitHub PAT (ghp_开头的Token): " GITHUB_PAT
    
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

# 加载环境变量以同步 Alist 密码
if [ -f "$CONFIG_PATH" ]; then
    export $(grep -v '^#' "$CONFIG_PATH" | xargs)
fi

# 7. 初始化 Alist 密码 (防止 Alist 无法登录)
echo "🔐 同步 Alist 管理员密码..."
# 设置数据目录，确保与 ecosystem.config.json 一致
export ALIST_DATA_DIR="./alist_data"
mkdir -p "$ALIST_DATA_DIR"

if command -v alist &> /dev/null; then
    # 尝试设置密码，静默输出
    # 注意：如果 user 不是 admin，这个命令可能只改 admin 的密码
    # 这里假设使用的是 admin 账户
    alist admin set "${ALIST_PASSWORD:-admin}" >/dev/null 2>&1
    echo "✅ Alist 'admin' 密码已重置为配置文件中的值"
else
    echo "⚠️ 未找到 alist 命令，跳过密码同步。请确认 alist 已安装。"
fi

# 8. 生成 PM2 Ecosystem 配置
echo "🤖 生成 PM2 配置..."
rm -f ecosystem.config.js ecosystem.config.cjs

cat <<EOF > ecosystem.config.json
{
  "apps": [
    {
      "name": "alist",
      "script": "alist",
      "args": "server",
      "interpreter": "none",
      "autorestart": true,
      "env": {
        "ALIST_DATA_DIR": "./alist_data"
      }
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

# 9. 设置 Termux 开机自启 (通过 .bashrc)
echo "🔄 配置 Termux 自动启动..."
if ! grep -q "pm2 resurrect" ~/.bashrc 2>/dev/null; then
    echo "pm2 resurrect >/dev/null 2>&1" >> ~/.bashrc
    echo "✅ 已添加 pm2 resurrect 到 .bashrc"
else
    echo "✅ 自启动配置已存在"
fi

echo "🎉 修复完成！正在重启所有服务..."
echo "------------------------------------------------"
pm2 delete all >/dev/null 2>&1
pm2 start ecosystem.config.json
pm2 save
echo "------------------------------------------------"
echo "✅ 所有服务已启动！"
echo "ℹ️  如果 Alist 仍然无法访问，请尝试等待 10-20 秒让其初始化。"
echo "ℹ️  Termux 下次打开时，Bot 将自动后台启动。"
echo "------------------------------------------------"
