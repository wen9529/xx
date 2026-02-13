import requests
import time
import json
import os
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
                # 优化 HTML 错误信息的显示
                preview = res.text[:200].replace('\n', ' ')
                return {"code": 500, "message": f"Alist 返回了无效数据 (HTML): {preview}..."}
            
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
         # 特别处理 storage not found 错误
         if "storage not found" in str(res.get('message')):
             # 尝试自动修复
             logger.info("检测到未配置存储，尝试自动初始化...")
             if init_default_storage():
                 # 重新尝试添加任务
                 return alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
         
         logger.info(f"v3 API 失败 ({res.get('message')})，尝试 v2 API...")
         res_old = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
         if res_old.get('code') == 200:
             return res_old
         else:
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
        return None, f"未找到直链 (raw_url 为空)。API数据: {str(res.get('data'))[:100]}"
        
    return url, None

def get_system_status():
    try:
        res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=5)
        return True if res.status_code == 200 else False
    except:
        return False

# --- 新增: 自动初始化存储 ---
def init_default_storage():
    """
    检查 Alist 是否有存储，如果没有，自动挂载 Termux 的 ~/downloads 目录到根目录 /
    """
    logger.info("检查 Alist 存储挂载状态...")
    res = alist_api("/api/admin/storage/list", method="GET")
    
    if res.get('code') == 200:
        content = res.get('data', {}).get('content', [])
        if len(content) > 0:
            logger.info(f"检测到已有 {len(content)} 个存储，跳过初始化。")
            return True
        else:
            logger.info("存储列表为空，正在添加默认本地存储...")
            # 构造本地存储配置
            home_dir = os.environ.get("HOME", "/data/data/com.termux/files/home")
            download_dir = os.path.join(home_dir, "downloads")
            
            # 确保目录存在
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            payload = {
                "mount_path": "/",
                "order": 0,
                "remark": "Termux Local",
                "cache_expiration": 30,
                "web_proxy": False,
                "webdav_policy": "302_redirect",
                "down_proxy_url": "",
                "extract_folder": "",
                "driver": "Local",
                "addition": json.dumps({
                    "root_folder_path": download_dir,
                    "thumbnail": False,
                    "thumb_cache_folder": "",
                    "show_hidden": True
                })
            }
            
            add_res = alist_api("/api/admin/storage/create", method="POST", data=payload)
            if add_res.get('code') == 200:
                logger.info("✅ 成功挂载本地存储到 /")
                return True
            else:
                logger.error(f"❌ 挂载存储失败: {add_res}")
                return False
    else:
        logger.error(f"无法获取存储列表: {res}")
        return False
