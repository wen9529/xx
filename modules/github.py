import requests
from config import GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT, ALIST_HOST, logger
from modules.tunnel import get_effective_public_url

def trigger_github_workflow(file_url, target_rtmp):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失"
    
    public_base = get_effective_public_url()
    final_url = file_url
    
    # 将内网链接转换为公网链接
    if public_base:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            if final_url.startswith("http"):
                 final_url = final_url.replace(ALIST_HOST, public_base).replace("http://127.0.0.1:5244", public_base)
            else:
                 final_url = f"{public_base}{final_url}"
    else:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            return False, "⚠️ 未开启远程访问 (隧道)，GitHub 无法连接内网文件。"

    logger.info(f"Stream URL: {final_url}")

    inputs = {"file_url": final_url, "rtmp_url": target_rtmp}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers, timeout=10)
        if res.status_code == 204:
            return True, "工作流已触发"
        else:
            return False, f"GitHub 错误 {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

def stop_all_workflows():
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
        runs = requests.get(url, headers=headers).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                requests.post(f"{url[:-19]}/runs/{run['id']}/cancel", headers=headers)
                count += 1
        return True, f"✅ 已停止 {count} 个任务。"
    except Exception as e:
        return False, f"❌ 停止失败: {e}"
