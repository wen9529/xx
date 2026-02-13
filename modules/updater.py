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
        
        if git_res.returncode != 0:
            return False, f"❌ **更新失败** (Git Error):\n\n`{git_res.stderr}`"
        
        stdout = git_res.stdout.strip()
        
        # 2. 检查是否有更新
        if "Already up to date" in stdout:
            return False, "✅ **系统已是最新版本**"
        
        # 3. 如果有更新，执行 setup.sh
        # 注意：现在 setup.sh 不会杀死 Bot，所以可以安全执行
        setup_res = subprocess.run(["bash", "setup.sh"], capture_output=True, text=True)
        
        log_msg = f"✅ **更新代码成功！**\n\n📄 **变更**: `{stdout[:100]}...`"
        
        if setup_res.returncode != 0:
            log_msg += f"\n\n⚠️ `setup.sh` 有警告:\n`{setup_res.stderr[:200]}`"
        else:
            log_msg += "\n\n🛠 依赖环境已更新。"
            
        log_msg += "\n\n🔄 **正在重启 Bot 以应用更改...**"
        
        return True, log_msg

    except Exception as e:
        return False, f"❌ **更新流程出错**: \n`{str(e)}`"
