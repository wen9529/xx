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

# --- 环境变量加载逻辑 (增强版) ---
# 1. 获取当前脚本所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. 定义可能的 .env 路径
LOCAL_ENV = os.path.join(BASE_DIR, '.env')
PARENT_ENV = os.path.abspath(os.path.join(BASE_DIR, '..', '.env')) # 上级目录

# 3. 强制加载逻辑
env_loaded = False

# 优先加载上级目录 (按照您的描述，配置文件在根目录)
if os.path.exists(PARENT_ENV):
    logger.info(f"正在加载配置文件: {PARENT_ENV}")
    load_dotenv(dotenv_path=PARENT_ENV, override=True)
    env_loaded = True

# 其次加载当前目录 (如果存在)
if os.path.exists(LOCAL_ENV):
    logger.info(f"正在加载配置文件: {LOCAL_ENV}")
    # 如果上级没加载，或者想用本地覆盖，这里加载
    load_dotenv(dotenv_path=LOCAL_ENV, override=not env_loaded)
    env_loaded = True

# --- 配置读取 ---
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")

# 检查关键配置
if not BOT_TOKEN:
    logger.error("❌ 严重错误: 未找到 TG_BOT_TOKEN")
    logger.error(f"已尝试路径: \n1. {PARENT_ENV} (存在: {os.path.exists(PARENT_ENV)})\n2. {LOCAL_ENV} (存在: {os.path.exists(LOCAL_ENV)})")
    logger.error("请检查文件内容是否包含 TG_BOT_TOKEN=your_token")
    sys.exit(1)

GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")
# Alist 配置
ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244").rstrip('/')
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")
ALIST_PUBLIC_URL_STATIC = os.getenv("ALIST_PUBLIC_URL", "").rstrip('/')

KEYS_FILE = os.path.join(BASE_DIR, "stream_keys.json")
CLOUDFLARED_BIN = os.path.join(BASE_DIR, "cloudflared")
