import requests
import json
from config import GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT, ALIST_HOST, logger
from modules.tunnel import get_effective_public_url

def trigger_github_workflow(file_url, target_rtmp):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失 (OWNER/REPO/PAT)，请检查 .env 文件。"
    
    public_base = get_effective_public_url()
    final_url = file_url
    
    # URL 转换与检查逻辑
    # 如果链接包含内网地址 (127.0.0.1 / localhost)，则需要替换为公网地址
    is_local_url = "127.0.0.1" in file_url or "localhost" in file_url
    
    if is_local_url:
        if public_base:
            # 替换本地 Host 为公网地址 (可以是 Cloudflare 隧道，也可以是 .env 配置的 ALIST_PUBLIC_URL)
            # 原始: http://127.0.0.1:5244/d/movie.mp4
            # 目标: https://xxxx.com/d/movie.mp4
            
            # 1. 尝试替换 ALIST_HOST (如果有端口)
            if ALIST_HOST in final_url:
                final_url = final_url.replace(ALIST_HOST, public_base)
            # 2. 尝试替换硬编码的默认地址
            elif "http://127.0.0.1:5244" in final_url:
                final_url = final_url.replace("http://127.0.0.1:5244", public_base)
            # 3. 兜底：如果是相对路径或只是 path，则拼接
            elif final_url.startswith("/"):
                 final_url = f"{public_base}{final_url}"
            else:
                 # 如果无法匹配替换，强制拼接可能会出错，但试试看
                 pass
            
            logger.info(f"URL 转换成功: {final_url}")
        else:
            # 没有公网地址，且是本地链接 -> 失败
            logger.warning("阻止推流: 本地链接且无公网 URL 配置")
            return False, (
                "⚠️ **无法推流**\n\n"
                "Alist 返回了内网下载地址 (127.0.0.1)，且系统未检测到公网访问地址。\n"
                "GitHub 服务器无法访问您的内网文件。\n\n"
                "👉 **请点击 '🌐 远程访问' 开启隧道，或在 .env 中配置 ALIST_PUBLIC_URL。**"
            )

    logger.info(f"🚀 触发 GitHub Workflow: \nFile: {final_url}\nTarget: {target_rtmp}")

    inputs = {"file_url": final_url, "rtmp_url": target_rtmp}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers, timeout=10)
        
        logger.info(f"GitHub API Code: {res.status_code}")
        
        if res.status_code == 204:
            return True, "✅ 指令已发送给 GitHub Actions。"
        elif res.status_code == 401:
            return False, "❌ 401 Unauthorized: GitHub Token (PAT) 无效或过期。"
        elif res.status_code == 404:
            return False, f"❌ 404 Not Found: 找不到仓库 {GITHUB_OWNER}/{GITHUB_REPO} 或 workflows/stream.yml 文件。"
        else:
            return False, f"GitHub API 异常 {res.status_code}:\n{res.text}"
            
    except Exception as e:
        logger.error(f"GitHub Trigger Exception: {e}")
        return False, f"网络请求异常: {str(e)}"

def stop_all_workflows():
    logger.info("尝试停止所有 GitHub 任务...")
    if not GITHUB_PAT:
        return False, "❌ 未配置 GitHub PAT"

    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
             return False, f"无法获取运行列表: {res.status_code}"
             
        runs = res.json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                logger.info(f"正在取消 Run ID: {run['id']}")
                requests.post(f"{url[:-19]}/runs/{run['id']}/cancel", headers=headers)
                count += 1
        
        if count == 0:
            return True, "✅ 当前没有正在运行的推流任务。"
        return True, f"✅ 已发送停止指令，共停止 {count} 个任务。"
    except Exception as e:
        logger.error(f"Stop workflows exception: {e}")
        return False, f"❌ 停止失败: {e}"
