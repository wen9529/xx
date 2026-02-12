import subprocess
import os
import asyncio
import re
from config import CLOUDFLARED_BIN, ALIST_HOST, ALIST_PUBLIC_URL_STATIC, logger

tunnel_process = None
current_public_url = None

async def start_cloudflared():
    global tunnel_process, current_public_url
    
    if tunnel_process and tunnel_process.poll() is None:
        return current_public_url

    if not os.path.exists(CLOUDFLARED_BIN):
        return None

    try:
        if os.path.exists("tunnel.log"): os.remove("tunnel.log")

        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", "tunnel.log"]
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        for i in range(20):
            await asyncio.sleep(1)
            if os.path.exists("tunnel.log"):
                with open("tunnel.log", "r") as f:
                    content = f.read()
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                    if match:
                        current_public_url = match.group(0)
                        return current_public_url
        
        stop_cloudflared()
        return None
    except Exception as e:
        logger.error(f"启动隧道失败: {e}")
        return None

def stop_cloudflared():
    global tunnel_process, current_public_url
    if tunnel_process:
        tunnel_process.terminate()
        tunnel_process = None
    current_public_url = None

def get_effective_public_url():
    if current_public_url: return current_public_url
    return ALIST_PUBLIC_URL_STATIC

def get_tunnel_status():
    return current_public_url
