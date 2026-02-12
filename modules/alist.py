import requests
import time
from config import ALIST_HOST, ALIST_USER, ALIST_PASSWORD, logger

alist_token = None

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        logger.info(f"Alist Login Attempt: {ALIST_HOST} User: {ALIST_USER}")
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                logger.info("✅ Alist Login Success")
                return alist_token
            else:
                logger.warning(f"❌ Alist 登录被拒绝: {data.get('message')}")
        else:
            logger.warning(f"❌ Alist API 状态码: {res.status_code}")
            
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ 无法连接到 Alist ({ALIST_HOST})。请检查 Alist 是否已启动。")
    except Exception as e:
        logger.error(f"❌ Alist 登录未知错误: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    global alist_token
    
    logger.debug(f"Alist API Call: {method} {endpoint}")

    for attempt in range(2):
        if not alist_token:
            if not get_alist_token():
                time.sleep(1)
                if not get_alist_token():
                    return {"code": 500, "message": "Alist 未连接或认证失败"}

        headers = {"Authorization": alist_token, "Content-Type": "application/json"}
        url = f"{ALIST_HOST}{endpoint}"
        
        try:
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=15)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=15)
                
            json_data = res.json()
            
            if res.status_code == 200 and json_data.get('code') == 401:
                logger.info("Alist Token 失效，刷新中...")
                alist_token = None
                continue 
            
            return json_data
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Alist 连接中断: {url}")
            return {"code": 500, "message": "无法连接到 Alist 服务"}
        except Exception as e:
            logger.error(f"❌ API 请求异常: {e}")
            return {"code": 500, "message": str(e)}
            
    return {"code": 500, "message": "请求失败 (重试后)"}

def add_aria2_task(url):
    logger.info(f"Adding Aria2 task: {url}")
    res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
    if res.get('code') != 200:
         logger.info("Failed v3 api, trying v2 api...")
         res_old = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
         if res_old.get('code') == 200:
             return res_old
    return res

def get_file_list(path, page):
    logger.info(f"Listing files: {path} page {page}")
    return alist_api("/api/fs/list", data={"path": path, "page": page, "per_page": 10})

def get_file_url(path):
    logger.info(f"Getting URL for: {path}")
    res = alist_api("/api/fs/get", data={"path": path})
    url = res.get('data', {}).get('raw_url')
    if not url:
        logger.error(f"Failed to get file URL. Response: {res}")
    return url, res.get('message')

def get_system_status():
    try:
        res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=5)
        return True if res.status_code == 200 else False
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return False
