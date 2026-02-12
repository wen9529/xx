import subprocess
import os
import asyncio
import re
import sys
from config import CLOUDFLARED_BIN, ALIST_HOST, ALIST_PUBLIC_URL_STATIC, logger, BASE_DIR

tunnel_process = None
current_public_url = None

async def start_cloudflared():
    global tunnel_process, current_public_url
    
    if tunnel_process and tunnel_process.poll() is None and current_public_url:
        return current_public_url

    if not os.path.exists(CLOUDFLARED_BIN):
        logger.error(f"Cloudflared binary not found at: {CLOUDFLARED_BIN}")
        return None
        
    try:
        log_file = os.path.join(BASE_DIR, "tunnel.log")
        if os.path.exists(log_file): os.remove(log_file)

        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", log_file]
        logger.info(f"Starting cloudflared: {' '.join(cmd)}")
        
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        logger.info("Cloudflared process started, waiting for URL...")
        
        for i in range(20):
            await asyncio.sleep(1)
            
            if tunnel_process.poll() is not None:
                logger.error(f"Cloudflared exited unexpectedly with code: {tunnel_process.returncode}")
                # Try to read why
                if os.path.exists(log_file):
                     with open(log_file, 'r', errors='ignore') as f:
                         logger.error(f"Tunnel Log Tail: {f.read()[-300:]}")
                return None

            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                        if match:
                            current_public_url = match.group(0)
                            logger.info(f"✅ Tunnel URL acquired: {current_public_url}")
                            return current_public_url
                except Exception:
                    pass
        
        logger.error("Timed out waiting for tunnel URL")
        stop_cloudflared()
        return None

    except Exception as e:
        logger.error(f"Start tunnel exception: {e}", exc_info=True)
        stop_cloudflared()
        return None

def stop_cloudflared():
    global tunnel_process, current_public_url
    logger.info("Stopping cloudflared...")
    if tunnel_process:
        try:
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
        except:
            pass
    tunnel_process = None
    current_public_url = None

def get_effective_public_url():
    if current_public_url: return current_public_url
    return ALIST_PUBLIC_URL_STATIC

def get_tunnel_status():
    if tunnel_process and tunnel_process.poll() is None:
        return current_public_url
    return None
