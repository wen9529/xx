import subprocess
import os
import asyncio
import re
import sys
import time
from config import CLOUDFLARED_BIN, ALIST_HOST, ALIST_PUBLIC_URL_STATIC, logger, BASE_DIR

tunnel_process = None
current_public_url = None

async def start_cloudflared():
    global tunnel_process, current_public_url
    
    # 检查当前状态
    if tunnel_process and tunnel_process.poll() is None and current_public_url:
        return current_public_url

    # 文件检查
    if not os.path.exists(CLOUDFLARED_BIN):
        logger.error(f"Cloudflared 未找到: {CLOUDFLARED_BIN}")
        return None
        
    # 权限检查
    if not os.access(CLOUDFLARED_BIN, os.X_OK):
        try:
            os.chmod(CLOUDFLARED_BIN, 0o755)
        except Exception as e:
            logger.error(f"无法设置 Cloudflared 执行权限: {e}")
            return None

    try:
        log_file = os.path.join(BASE_DIR, "tunnel.log")
        # 清理旧日志
        if os.path.exists(log_file): os.remove(log_file)

        # 启动命令
        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", log_file]
        logger.info(f"启动 Cloudflare 隧道: {' '.join(cmd)}")
        
        # 启动进程 (不捕获 stdout/stderr，让它写到 logfile 或系统日志)
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 轮询日志文件查找 URL
        found_url = None
        for i in range(30): # 增加到 30 秒超时
            await asyncio.sleep(1)
            
            # 检查进程是否意外退出
            if tunnel_process.poll() is not None:
                logger.error(f"Cloudflared 进程意外退出，退出码: {tunnel_process.returncode}")
                # 尝试读取日志查看原因
                if os.path.exists(log_file):
                    with open(log_file, "r", errors="ignore") as f:
                        logger.error(f"失败日志: {f.read()[-500:]}")
                return None

            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # 查找 trycloudflare.com
                        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                        if match:
                            found_url = match.group(0)
                            break
                except Exception:
                    pass
        
        if found_url:
            current_public_url = found_url
            logger.info(f"✅ 隧道建立成功: {current_public_url}")
            return current_public_url
        else:
            logger.error("❌ 隧道启动超时，未能获取 URL。")
            stop_cloudflared()
            return None

    except Exception as e:
        logger.error(f"启动隧道异常: {e}")
        stop_cloudflared()
        return None

def stop_cloudflared():
    global tunnel_process, current_public_url
    if tunnel_process:
        try:
            tunnel_process.terminate()
            tunnel_process.wait(timeout=3)
        except:
            if tunnel_process: tunnel_process.kill()
    tunnel_process = None
    current_public_url = None

def get_effective_public_url():
    if current_public_url: return current_public_url
    return ALIST_PUBLIC_URL_STATIC

def get_tunnel_status():
    return current_public_url
