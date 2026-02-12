#!/bin/bash

echo "🚀 开始 StreamForge 环境智能部署..."

# 函数：检查并安装软件包
check_install() {
    if ! command -v $1 &> /dev/null; then
        echo "📦 正在安装 $2..."
        pkg install -y $2
    else
        echo "✅ $1 已安装，跳过。"
    fi
}

# 1. 更新软件源
echo "🔄 正在同步软件源..."
pkg update -y

# 2. 检查基础软件包
check_install python python
check_install alist alist
check_install ffmpeg ffmpeg
check_install git git
check_install node nodejs

# 3. 检查 PM2 (Node.js 模块)
if ! command -v pm2 &> /dev/null; then
    echo "📦 正在安装 PM2 进程管理器..."
    npm install -g pm2
else
    echo "✅ PM2 已安装，跳过。"
fi

# 4. 检查并更新 Python 依赖
echo "📦 检查 Python 依赖库 (telegram, requests, dotenv)..."
pip install python-telegram-bot requests python-dotenv --upgrade

# 5. 配置并启动服务 (使用 PM2)
echo "⚙️ 配置服务自动化..."

# 停止并删除旧的 PM2 任务以免重复
pm2 delete alist stream-bot 2>/dev/null

# 启动 Alist
echo "▶️ 启动 Alist 服务..."
pm2 start alist --name alist -- server

# 启动 Bot
if [ -f "bot.py" ]; then
    echo "▶️ 启动 Telegram Bot..."
    pm2 start bot.py --name stream-bot --interpreter python
else
    echo "❌ 错误: 未在当前目录找到 bot.py 文件！"
    echo "请先确保 bot.py 内容已正确保存到本地。"
fi

# 6. 保存 PM2 状态以实现持久化
pm2 save

echo ""
echo "🎉 部署脚本执行完毕！"
echo "--------------------------------"
echo "📊 当前运行状态:"
pm2 status
echo "--------------------------------"
echo "💡 提示:"
echo "- 查看日志: pm2 logs stream-bot"
echo "- 重启 Bot: pm2 restart stream-bot"
echo "- Alist 地址: http://127.0.0.1:5244"
echo "--------------------------------"
