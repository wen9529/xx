import time
import subprocess
import sys
import datetime

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [Watcher] {msg}", flush=True)

def check_updates():
    log("🔍 正在检查代码更新...")
    try:
        # 1. 执行 Git Pull
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if result.returncode != 0:
            log(f"❌ Git 拉取失败: {result.stderr}")
            return

        stdout = result.stdout.strip()

        # 2. 检查是否有 Git 变化
        if "Already up to date" in stdout:
            log("✅ 代码已是最新")
            return

        log("⬇️ 检测到更新！正在应用更改...")
        log(f"📄 Git 输出:\n{stdout}")

        # 3. 运行 setup.sh 来修复依赖和配置
        # setup.sh 必须存在且有执行权限
        setup_res = subprocess.run(["bash", "setup.sh"], capture_output=True, text=True)
        if setup_res.returncode == 0:
            log("✅ setup.sh 执行成功")
        else:
            log(f"⚠️ setup.sh 执行遇到问题: {setup_res.stderr}")

        # 4. 重启 Bot
        # 即使 bot.py 挂了，PM2 也会尝试重启它。
        # 但如果是代码语法错误，PM2 可能会停止重启。
        # 这里强制重启 stream-bot 进程，让它加载新代码。
        log("🔄 正在重启 Stream Bot...")
        subprocess.run(["pm2", "restart", "stream-bot"], capture_output=True)
        log("🎉 更新应用完成")

    except Exception as e:
        log(f"⚠️ 自动更新过程发生异常: {e}")

if __name__ == "__main__":
    log("🚀 自动更新看门狗 (Watcher) 已启动")
    log("🛡️ 即使 Bot 崩溃，我也会每 5 分钟检查一次代码修复。")
    
    # 启动时先检查一次
    check_updates()
    
    # 循环检查
    while True:
        time.sleep(300) # 300秒 = 5分钟
        check_updates()
