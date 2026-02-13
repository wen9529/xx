import requests
import time
import json
from config import ALIST_HOST, ALIST_USER, ALIST_PASSWORD, logger

alist_token = None

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        logger.info(f"尝试登录 Alist: {url} 用户: {ALIST_USER}")
        
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                logger.info("✅ Alist 登录成功")
                return alist_token
            else:
                logger.error(f"❌ Alist 登录被拒绝: {data}")
                return None
        else:
            logger.error(f"❌ Alist API HTTP 错误: {res.status_code} - {res.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ 无法连接到 Alist ({ALIST_HOST})。请检查 Alist 是否运行中。")
    except Exception as e:
        logger.error(f"❌ Alist 登录发生异常: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    global alist_token
    
    url = f"{ALIST_HOST}{endpoint}"
    logger.debug(f"Alist API 请求: {method} {url}")

    # 重试机制
    for attempt in range(2):
        if not alist_token:
            if not get_alist_token():
                if attempt == 0:
                    time.sleep(1)
                    continue
                return {"code": 500, "message": f"无法登录 Alist，请检查账号密码或服务状态。\nHost: {ALIST_HOST}"}

        headers = {"Authorization": alist_token, "Content-Type": "application/json"}
        
        try:
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=15)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=15)
                
            try:
                json_data = res.json()
            except json.JSONDecodeError:
                return {"code": 500, "message": f"Alist 返回了非 JSON 数据 (状态码 {res.status_code}):\n{res.text[:200]}"}
            
            # Token 过期处理
            if res.status_code == 200 and json_data.get('code') == 401:
                logger.warning("Alist Token 已失效，正在刷新...")
                alist_token = None
                continue 
            
            return json_data
            
        except requests.exceptions.ConnectionError:
            return {"code": 500, "message": f"连接被拒绝: {url}\nAlist 可能未启动。"}
        except requests.exceptions.Timeout:
            return {"code": 500, "message": f"请求超时: {url}"}
        except Exception as e:
            logger.error(f"API 请求异常: {e}", exc_info=True)
            return {"code": 500, "message": f"Python 请求异常: {str(e)}"}
            
    return {"code": 500, "message": "请求失败 (重试次数耗尽)"}

def add_aria2_task(url):
    logger.info(f"添加 Aria2 任务: {url}")
    # 尝试 v3 API
    res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
    
    if res.get('code') != 200:
         logger.info(f"v3 API 失败 ({res.get('message')})，尝试 v2 API...")
         res_old = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
         if res_old.get('code') == 200:
             return res_old
         else:
             # 如果两者都失败，返回 v3 的错误信息，通常更准确
             # 或者合并错误信息
             res['message'] = f"v3: {res.get('message')} | v2: {res_old.get('message')}"
    return res

def get_file_list(path, page):
    logger.info(f"获取文件列表: {path} (Page {page})")
    return alist_api("/api/fs/list", data={"path": path, "page": page, "per_page": 10})

def get_file_url(path):
    logger.info(f"获取文件详情: {path}")
    res = alist_api("/api/fs/get", data={"path": path})
    
    if res.get('code') != 200:
        return None, f"API 错误: {res.get('message')}"
        
    url = res.get('data', {}).get('raw_url')
    if not url:
        # 有时候 raw_url 为空，可能是文件夹或者权限问题
        return None, f"未找到直链 (raw_url 为空)。API数据: {str(res.get('data'))[:100]}"
        
    return url, None

def get_system_status():
    try:
        res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=5)
        return True if res.status_code == 200 else False
    except:
        return False
