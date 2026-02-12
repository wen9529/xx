#!/bin/bash

echo "🚀 开始 StreamForge 环境部署..."

# 1. 更新 Termux 源并安装基础包
echo "📦 正在更新软件源并安装依赖 (Python, Alist, FFmpeg, Node.js)..."
pkg update -y
pkg install -y python alist ffmpeg git nodejs

# 2. 安装 PM2 (用于后台进程管理)
echo "📦 正在安装 PM2..."
npm install -g pm2

# 3. 安装 Python 依赖库
echo "📦 正在安装 Python 库 (Telegram Bot, Requests)..."
pip install python-telegram-bot requests python-dotenv

# 4. 启动 Alist (如果尚未运行)
echo "⚙️ 启动 Alist 服务..."
# 使用 PM2 管理 Alist，避免后台被杀
pm2 start alist --name alist -- server

# 5. 启动 Telegram Bot
echo "🤖 启动 Bot..."
# 确保 bot.py 存在
if [ -f "bot.py" ]; then
    pm2 start bot.py --name stream-bot --interpreter python
    echo "✅ Bot 已通过 PM2 启动"
else
    echo "⚠️ 未找到 bot.py，请确保文件已保存，然后手动运行: pm2 start bot.py --interpreter python"
fi

# 6. 保存 PM2 状态 (开机自启)
pm2 save

echo "🎉 部署完成！"
echo "👉 Alist 地址: http://127.0.0.1:5244 (默认密码请查看 Alist 文档或终端输出)"
echo "👉 Bot 状态: 使用 'pm2 status' 查看"
