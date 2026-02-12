import requests
import json
from config import GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT, ALIST_HOST, logger
from modules.tunnel import get_effective_public_url

def trigger_github_workflow(file_url, target_rtmp):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失 (OWNER/REPO/PAT)"
    
    public_base = get_effective_public_url()
    final_url = file_url
    
    # URL 转换逻辑
    if public_base:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            if final_url.startswith("http"):
                 # 简单替换 host
                 final_url = final_url.replace(ALIST_HOST, public_base).replace("http://127.0.0.1:5244", public_base)
            else:
                 final_url = f"{public_base}{final_url}"
            logger.info(f"Converted Local URL to Public URL: {final_url}")
    else:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            logger.warning("Using Local URL without Tunnel, GitHub will likely fail.")
            return False, "⚠️ 未开启远程访问 (隧道)，GitHub 无法连接内网文件。"

    logger.info(f"🚀 Triggering Workflow: File={final_url}, Target={target_rtmp}")

    inputs = {"file_url": final_url, "rtmp_url": target_rtmp}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers, timeout=10)
        
        logger.info(f"GitHub API Response: {res.status_code} - {res.text}")
        
        if res.status_code == 204:
            return True, "工作流已成功触发"
        else:
            return False, f"GitHub 错误 {res.status_code}: {res.text}"
    except Exception as e:
        logger.error(f"GitHub Trigger Exception: {e}")
        return False, str(e)

def stop_all_workflows():
    logger.info("Attempting to stop all workflows...")
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
        runs = requests.get(url, headers=headers).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                logger.info(f"Cancelling Run ID: {run['id']}")
                requests.post(f"{url[:-19]}/runs/{run['id']}/cancel", headers=headers)
                count += 1
        return True, f"✅ 已停止 {count} 个任务。"
    except Exception as e:
        logger.error(f"Stop workflows exception: {e}")
        return False, f"❌ 停止失败: {e}"
