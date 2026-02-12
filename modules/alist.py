import requests
import time
from config import ALIST_HOST, ALIST_USER, ALIST_PASSWORD, logger

alist_token = None

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        # 增加超时时间
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
            else:
                logger.warning(f"Alist 登录被拒绝: {data.get('message')}")
        else:
            logger.warning(f"Alist API 返回状态码: {res.status_code}")
            
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到 Alist ({ALIST_HOST})。服务可能未启动或正在初始化。")
    except Exception as e:
        logger.error(f"Alist 登录未知错误: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    global alist_token
    
    # 简单的重试逻辑
    for _ in range(2):
        if not alist_token:
            if not get_alist_token():
                # 如果获取 token 失败，稍微等待再试一次（可能是服务刚启动）
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
            
            # Token 过期处理
            if res.status_code == 200 and json_data.get('code') == 401:
                logger.info("Alist Token 失效，正在刷新...")
                alist_token = None # 清空 token 触发下一次循环的重新获取
                continue 
            
            return json_data
            
        except requests.exceptions.ConnectionError:
            logger.error("Alist 连接中断")
            return {"code": 500, "message": "无法连接到 Alist 服务"}
        except Exception as e:
            logger.error(f"API 请求错误: {e}")
            return {"code": 500, "message": str(e)}
            
    return {"code": 500, "message": "请求失败 (重试后)"}

def add_aria2_task(url):
    # 优先尝试 v3 接口
    res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
    # 如果 v3 接口不存在 (404) 或报错，尝试旧接口
    if res.get('code') != 200:
         res_old = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
         # 如果旧接口成功，返回旧接口结果
         if res_old.get('code') == 200:
             return res_old
    return res

def get_file_list(path, page):
    return alist_api("/api/fs/list", data={"path": path, "page": page, "per_page": 10})

def get_file_url(path):
    res = alist_api("/api/fs/get", data={"path": path})
    return res.get('data', {}).get('raw_url'), res.get('message')

def get_system_status():
    try:
        # 增加超时
        res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=5)
        return True if res.status_code == 200 else False
    except:
        return False
