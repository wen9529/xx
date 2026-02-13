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

        # 关键修改: 
        # 1. --protocol http2: 解决部分网络环境下 QUIC 被阻断的问题
        # 2. --no-autoupdate: 防止因权限不足尝试更新而崩溃
        cmd = [
            CLOUDFLARED_BIN, "tunnel", 
            "--url", ALIST_HOST, 
            "--protocol", "http2", 
            "--no-autoupdate",
            "--logfile", log_file
        ]
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            # 捕获 Exec format error (通常是二进制架构不对)
            if e.errno == 8: # Exec format error
                logger.error(f"Cloudflared 无法运行 (架构不兼容): {e}")
                try: os.remove(CLOUDFLARED_BIN) 
                except: pass
                return None, "❌ Cloudflared 二进制文件架构不兼容或已损坏。\n已自动删除错误文件。\n请重新发送 '🔄 更新系统' 来重新下载正确版本。"
            raise e
        
        logger.info("Cloudflared 进程已启动，等待 URL 生成...")
        
        # 等待最多 30 秒 (HTTP2 连接可能稍慢)
        for i in range(30):
            await asyncio.sleep(1)
            
            # 检查进程是否过早退出
            if tunnel_process.poll() is not None:
                err_code = tunnel_process.returncode
                logger.error(f"Cloudflared 意外退出，退出码: {err_code}")
                
                # 读取日志查找原因
                log_content = _read_log_tail(log_file, lines=20)
                
                suggestion = ""
                if "Code 1" in str(err_code) or err_code == 1:
                    suggestion = "\n\n💡 **提示**: Code 1 通常是网络或 DNS 问题。脚本已尝试使用 http2 协议修复。"
                
                return None, f"🚫 进程意外退出 (Code {err_code})。{suggestion}\n📜 日志:\n{log_content}"

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
                        
                        if "bind: address already in use" in content:
                            return None, "端口被占用，请尝试重启 Termux。"
                except Exception as e:
                    logger.warning(f"读取日志文件出错: {e}")
        
        # 超时处理
        stop_cloudflared()
        return None, "启动超时，未在日志中找到 URL。可能是网络连接过慢。"

    except Exception as e:
        logger.error(f"启动隧道发生异常: {e}", exc_info=True)
        stop_cloudflared()
        return None, f"系统异常: {str(e)}"

def _read_log_tail(filepath, lines=10):
    if not os.path.exists(filepath): return "无日志文件"
    try:
        with open(filepath, 'r', errors='ignore') as f:
            return "".join(f.readlines()[-lines:])
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
