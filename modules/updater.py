import subprocess
import os
import sys

def update_repo():
    """
    拉取 Git 仓库更新 (供 Bot 按钮调用)
    返回: (bool 是否需要重启, str 提示消息)
    """
    try:
        # 1. 执行 Git Pull
        git_res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if git_res.returncode != 0:
            return False, f"❌ **更新失败** (Git Error):\n\n`{git_res.stderr}`"
        
        stdout = git_res.stdout.strip()
        
        # 2. 检查是否有更新
        if "Already up to date" in stdout:
            return False, "✅ **系统已是最新版本**\n无需更新。"
        
        # 3. 如果有更新，执行 setup.sh
        setup_res = subprocess.run(["bash", "setup.sh"], capture_output=True, text=True)
        
        log_msg = f"✅ **更新成功！**\n\n📄 **变更日志**:\n`{stdout[:200]}...`"
        
        if setup_res.returncode != 0:
            log_msg += f"\n\n⚠️ **警告**: `setup.sh` 执行有误:\n`{setup_res.stderr}`"
        else:
            log_msg += "\n\n🛠 `setup.sh` 已自动执行。"
            
        log_msg += "\n\n🔄 **正在重启 Bot...**"
        
        return True, log_msg

    except Exception as e:
        return False, f"❌ **更新错误**: \n`{str(e)}`"
