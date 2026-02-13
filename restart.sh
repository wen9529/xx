#!/bin/bash
echo "🛑 正在停止所有服务..."
pm2 stop all

echo "🧹 清理缓存..."
rm -f __pycache__/*.pyc
rm -f modules/__pycache__/*.pyc

echo "🚀 重新启动服务..."
pm2 restart ecosystem.config.json
pm2 save --force

echo "✅ 服务已重启！Bot 应该加载了最新代码。"
