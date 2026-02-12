import time
import subprocess
import sys
import datetime

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def check_updates():
    log("🔍 正在检查代码更新...")
    try:
        # 1. 执行 Git Pull
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if result.returncode != 0:
            log(f"❌ Git 拉取失败: {result.stderr}")
            return

        stdout = result.stdout.strip()

        # 2. 检查是否有变化
        if "Already up to date" in stdout:
            log("✅ 系统已是最新")
            return

        log("⬇️ 检测到更新！正在应用更改...")
        log(f"📄 Git 输出:\n{stdout}")

        # 3. 如果有更新，运行 setup.sh (修复依赖/配置)
        setup_res = subprocess.run(["bash", "setup.sh"], capture_output=True, text=True)
        if setup_res.returncode == 0:
            log("✅ setup.sh 执行成功")
        else:
            log(f"⚠️ setup.sh 执行遇到问题: {setup_res.stderr}")

        # 4. 重启 Stream Bot 进程
        # 注意：这里我们只重启 bot，不重启 watcher 自己
        log("🔄 正在重启 Stream Bot...")
        subprocess.run(["pm2", "restart", "stream-bot"], capture_output=True)
        log("🎉 更新流程完成")

    except Exception as e:
        log(f"⚠️ 自动更新过程发生错误: {e}")

if __name__ == "__main__":
    log("🚀 自动更新看门狗 (Watcher) 已启动")
    log("⏱️ 每 300 秒 (5分钟) 检查一次更新")
    
    # 启动时先检查一次
    check_updates()
    
    while True:
        time.sleep(300)
        check_updates()
