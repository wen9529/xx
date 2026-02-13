import subprocess
import os
import asyncio
import re
import sys
from config import CLOUDFLARED_BIN, ALIST_HOST, ALIST_PUBLIC_URL_STATIC, logger, BASE_DIR

tunnel_process = None
current_public_url = None

async def start_cloudflared():
    """
    启动 Cloudflared 隧道
    返回: (url, error_message)
    如果成功，url 为地址，error_message 为 None
    如果失败，url 为 None，error_message 为日志内容的最后几行
    """
    global tunnel_process, current_public_url
    
    if tunnel_process and tunnel_process.poll() is None and current_public_url:
        return current_public_url, None

    if not os.path.exists(CLOUDFLARED_BIN):
        msg = f"Cloudflared 二进制文件未找到: {CLOUDFLARED_BIN}"
        logger.error(msg)
        return None, msg
        
    try:
        log_file = os.path.join(BASE_DIR, "tunnel.log")
        if os.path.exists(log_file): os.remove(log_file)

        # 增加 --protocol http2 可能有助于稳定性，视情况而定
        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", log_file]
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        logger.info("Cloudflared 进程已启动，等待 URL 生成...")
        
        # 等待最多 20 秒
        for i in range(20):
            await asyncio.sleep(1)
            
            # 检查进程是否过早退出
            if tunnel_process.poll() is not None:
                err_code = tunnel_process.returncode
                logger.error(f"Cloudflared 意外退出，退出码: {err_code}")
                log_content = _read_log_tail(log_file)
                return None, f"进程意外退出 (Code {err_code})。\n日志末尾:\n{log_content}"

            # 检查日志文件
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # 匹配 trycloudflare.com
                        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                        if match:
                            current_public_url = match.group(0)
                            logger.info(f"✅ 获取到隧道 URL: {current_public_url}")
                            return current_public_url, None
                        
                        # 检查常见错误
                        if "bind: address already in use" in content:
                            return None, "端口被占用，请尝试重启 Termux 或杀掉旧进程。"
                        if "Error" in content and "Retrying" not in content:
                            # 简单的错误捕获
                            pass
                except Exception as e:
                    logger.warning(f"读取日志文件出错: {e}")
        
        # 超时处理
        logger.error("等待隧道 URL 超时")
        log_content = _read_log_tail(log_file)
        stop_cloudflared()
        return None, f"启动超时 (20s)，未在日志中找到 URL。\n日志末尾:\n{log_content}"

    except Exception as e:
        logger.error(f"启动隧道发生异常: {e}", exc_info=True)
        stop_cloudflared()
        return None, f"Python 异常: {str(e)}"

def _read_log_tail(filepath, lines=15):
    """读取日志文件末尾 n 行"""
    if not os.path.exists(filepath):
        return "日志文件不存在"
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except:
        return "无法读取日志"

def stop_cloudflared():
    global tunnel_process, current_public_url
    logger.info("正在停止 Cloudflared...")
    if tunnel_process:
        try:
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
        except Exception as e:
            logger.error(f"停止进程出错: {e}")
    tunnel_process = None
    current_public_url = None

def get_effective_public_url():
    if current_public_url: return current_public_url
    return ALIST_PUBLIC_URL_STATIC

def get_tunnel_status():
    if tunnel_process and tunnel_process.poll() is None:
        return current_public_url
    return None
