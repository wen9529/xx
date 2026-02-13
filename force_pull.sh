#!/bin/bash

echo "⚠️  警告：即将强制覆盖本地所有文件..."
echo "⏳ 正在连接 GitHub..."

# 1. 清理可能的 Git 锁文件
rm -f .git/index.lock

# 2. 强制同步
git fetch --all
# 确保切换回主分支
git checkout main >/dev/null 2>&1
# 强制重置指针到远程最新
git reset --hard origin/main
git pull

echo "✅ 代码已强制同步到最新版本。"

# 3. 赋予脚本执行权限
chmod +x *.sh

# 4. 重新运行安装脚本以应用更改
echo "🛠 正在重新配置环境..."
bash setup.sh

# 5. 确保重启
pm2 restart all
echo "🎉 修复完成！现在菜单应该是最新的了。"
