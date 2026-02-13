import subprocess
import os
import sys

def update_repo():
    """
    拉取 Git 仓库更新 (供 Bot 按钮调用)
    """
    try:
        # 1. 执行 Git Pull
        git_res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        # Git 失败通常是因为本地有修改冲突
        if git_res.returncode != 0:
            err_msg = (
                f"⚠️ **自动更新失败**\n\n"
                f"Git 报错:\n`{git_res.stderr}`\n\n"
                f"🔧 **解决方法**:\n"
                f"请在 Termux 终端手动运行:\n`bash force_pull.sh`"
            )
            return False, err_msg
        
        stdout = git_res.stdout.strip()
        
        # 2. 检查是否有更新
        log_msg = ""
        if "Already up to date" in stdout:
            log_msg = "✅ **系统已是最新版本**"
        else:
            # 3. 如果有 Git 更新，执行 setup.sh
            setup_res = subprocess.run(["bash", "setup.sh"], capture_output=True, text=True)
            log_msg = f"✅ **更新代码成功！**\n📄 `{stdout[:100]}...`"
            if setup_res.returncode != 0:
                log_msg += f"\n\n⚠️ `setup.sh` 警告:\n`{setup_res.stderr[:200]}`"

        log_msg += "\n\n🔄 **正在重启 Bot...**"
        
        # 无论是否有更新，都尝试重启以刷新缓存
        return True, log_msg

    except Exception as e:
        return False, f"❌ **更新流程出错**: \n`{str(e)}`"
