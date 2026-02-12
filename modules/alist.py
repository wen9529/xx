import requests
from config import ALIST_HOST, ALIST_USER, ALIST_PASSWORD, logger

alist_token = None

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
    except Exception as e:
        logger.error(f"Alist 登录失败: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    global alist_token
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    url = f"{ALIST_HOST}{endpoint}"
    
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=10)
        else:
            res = requests.post(url, json=data, headers=headers, timeout=10)
            
        # 如果 Token 过期 (Code 401)，重新登录并重试一次
        if res.status_code == 200 and res.json().get('code') == 401:
            headers["Authorization"] = get_alist_token()
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=10)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"code": 500, "message": str(e)}

def add_aria2_task(url):
    # 尝试多种 API 路径以兼容不同版本的 Alist
    res = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
    if res.get('code') != 200:
        res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
    return res

def get_file_list(path, page):
    return alist_api("/api/fs/list", data={"path": path, "page": page, "per_page": 10})

def get_file_url(path):
    res = alist_api("/api/fs/get", data={"path": path})
    return res.get('data', {}).get('raw_url'), res.get('message')

def get_system_status():
    try:
        res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=2)
        return True if res.status_code == 200 else False
    except:
        return False
