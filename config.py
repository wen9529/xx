import os
import sys
import logging
from dotenv import load_dotenv

# --- 日志配置 ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("StreamForge")

# --- 加载环境变量 ---
load_dotenv()

# 如果当前目录没有 Token，尝试加载上级目录的 .env
if not os.getenv("TG_BOT_TOKEN"):
    parent_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(parent_env):
        logger.info(f"正在加载上级目录配置文件: {parent_env}")
        load_dotenv(dotenv_path=parent_env)

# 配置常量
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")
ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244").rstrip('/')
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")
ALIST_PUBLIC_URL_STATIC = os.getenv("ALIST_PUBLIC_URL", "").rstrip('/')

KEYS_FILE = "stream_keys.json"
CLOUDFLARED_BIN = "./cloudflared"

if not BOT_TOKEN:
    logger.error("❌ 未找到 TG_BOT_TOKEN，请检查 .env 文件")
    sys.exit(1)
