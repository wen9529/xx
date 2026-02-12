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

# --- 环境变量加载逻辑 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ENV = os.path.join(BASE_DIR, '.env')
PARENT_ENV = os.path.abspath(os.path.join(BASE_DIR, '..', '.env'))

env_loaded = False
if os.path.exists(PARENT_ENV):
    load_dotenv(dotenv_path=PARENT_ENV, override=True)
    env_loaded = True

if os.path.exists(LOCAL_ENV):
    load_dotenv(dotenv_path=LOCAL_ENV, override=not env_loaded)
    env_loaded = True

# --- 配置读取 ---
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")

if not BOT_TOKEN:
    logger.error("❌ 未找到 TG_BOT_TOKEN")
    sys.exit(1)

GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")

# 修复 RTMP_URL 逻辑：确保作为基础 URL 使用
_raw_rtmp = os.getenv("RTMP_URL", "")
# 如果不为空且不以 / 结尾，加上 /
if _raw_rtmp and not _raw_rtmp.endswith('/'):
    RTMP_URL = _raw_rtmp + "/"
else:
    RTMP_URL = _raw_rtmp

ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244").rstrip('/')
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")
ALIST_PUBLIC_URL_STATIC = os.getenv("ALIST_PUBLIC_URL", "").rstrip('/')

KEYS_FILE = os.path.join(BASE_DIR, "stream_keys.json")
CLOUDFLARED_BIN = os.path.join(BASE_DIR, "cloudflared")
