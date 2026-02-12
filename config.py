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
# 1. 尝试加载当前目录的 .env
load_dotenv()

# 2. 如果当前目录没有 Token (或为空)，尝试加载上级目录的 .env
# 注意：如果本地 .env 存在但变量为空，load_dotenv 可能会将其置为空字符串
if not os.getenv("TG_BOT_TOKEN"):
    parent_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(parent_env):
        logger.info(f"正在加载上级目录配置文件: {parent_env}")
        # 关键: 使用 override=True 覆盖本地可能存在的空值，解决本地有空 .env 导致的问题
        load_dotenv(dotenv_path=parent_env, override=True)

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
    logger.error("❌ 未找到 TG_BOT_TOKEN，请检查 .env 文件 (已检查当前及上级目录)")
    sys.exit(1)
