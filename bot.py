import os
import logging
import requests
import mimetypes
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")
DEFAULT_COVER = os.getenv("DEFAULT_COVER", "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=1920&auto=format&fit=crop")

ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244")
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

alist_token = None

# --- Helpers ---
def get_alist_token():
    global alist_token
    try:
        res = requests.post(f"{ALIST_HOST}/api/auth/login", json={"username": ALIST_USER, "password": ALIST_PASSWORD})
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
    except Exception as e: logger.error(f"Login Error: {e}")
    return None

def alist_req(endpoint, data=None):
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        url = f"{ALIST_HOST}{endpoint}"
        res = requests.post(url, json=data, headers=headers)
        if res.json().get('code') == 401:
            headers["Authorization"] = get_alist_token()
            res = requests.post(url, json=data, headers=headers)
        return res.json()
    except: return {}

def github_api(method, endpoint, json_data=None):
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/{endpoint}"
    if method == "POST": return requests.post(url, json=json_data, headers=headers)
    if method == "GET": return requests.get(url, headers=headers)
    return None

def is_audio_file(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime and mime.startswith('audio'): return True
    ext = filename.lower().split('.')[-1]
    return ext in ['mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']

# --- Handlers ---
async def start(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    kb = [["📂 浏览文件", "🛑 停止推流"], ["ℹ️ 帮助", "⚙️ 状态"]]
    await update.message.reply_text("👋 *StreamForge Ultimate*", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    if msg == "📂 浏览文件": await show_dir(update, "/", 1)
    elif msg == "🛑 停止推流": await stop_stream(update)
    elif msg == "⚙️ 状态": await update.message.reply_text(f"Bot运行中\nAlist: {'✅' if alist_token else '❌'}")
    elif msg == "ℹ️ 帮助": await update.message.reply_text("支持视频直推及音频+封面自动合成推流。")
    elif msg.startswith("http"): 
        await update.message.reply_text(f"🔗 检测到链接，准备推流...")
        await trigger_stream(update, msg, "Direct Link")

async def show_dir(obj, path, page):
    data = alist_req("/api/fs/list", {"path": path, "page": page, "per_page": 10})
    content = data.get('data', {}).get('content', [])
    total = data.get('data', {}).get('total', 0)
    content.sort(key=lambda x: x['is_dir'], reverse=True)
    
    kb = []
    if path != "/":
        parent = os.path.dirname(path.rstrip('/')) or "/"
        kb.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"nav|{parent}|1")])
    
    for f in content:
        name = f['name']
        fp = f"{path.rstrip('/')}/{name}"
        icon = "📁" if f['is_dir'] else ("🎵" if is_audio_file(name) else "🎬")
        
        if f['is_dir']: kb.append([InlineKeyboardButton(f"{icon} {name}", callback_data=f"nav|{fp}|1")])
        else: kb.append([InlineKeyboardButton(f"{icon} {name}", callback_data=f"play|{fp}")])

    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav|{path}|{page-1}"))
    if page * 10 < total: nav_row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"nav|{path}|{page+1}"))
    if nav_row: kb.append(nav_row)

    markup = InlineKeyboardMarkup(kb)
    txt = f"📂 路径: `{path}`\n📄 页码: {page}"
    if isinstance(obj, Update): await obj.message.reply_text(txt, reply_markup=markup, parse_mode='Markdown')
    else: await obj.callback_query.edit_message_text(txt, reply_markup=markup, parse_mode='Markdown')

async def trigger_stream(obj, url, name):
    target = obj.message if isinstance(obj, Update) else obj.callback_query
    
    inputs = {"file_url": url, "rtmp_url": RTMP_URL}
    mode_text = "🎬 视频模式"
    
    # Auto-detect audio mode
    if is_audio_file(name):
        mode_text = "🎵 音频+封面模式"
        inputs["image_url"] = DEFAULT_COVER 
        
    status_msg = await target.reply_text(f"🚀 启动 GitHub Actions...\n{mode_text}\n📄 内容: {name}")
    
    res = github_api("POST", "actions/workflows/stream.yml/dispatches", {
        "ref": "main",
        "inputs": inputs
    })
    
    if res.status_code == 204:
        await status_msg.edit_text(f"✅ 推流任务已提交! ({mode_text})\n📺 请关注直播间。")
    else:
        await status_msg.edit_text(f"❌ 启动失败: {res.status_code}\n{res.text}")

async def stop_stream(update):
    msg = await update.message.reply_text("🔍 正在查找运行中的任务...")
    runs = github_api("GET", "actions/runs?status=in_progress").json()
    count = 0
    if 'workflow_runs' in runs:
        for run in runs['workflow_runs']:
            if run['name'] == 'Alist Stream to Telegram':
                github_api("POST", f"actions/runs/{run['id']}/cancel")
                count += 1
    await msg.edit_text(f"🛑 已发送取消指令给 {count} 个任务。")

async def cb_handler(update: Update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("|")
    action = parts[0]
    
    if action == "nav": await show_dir(update, parts[1], int(parts[2]))
    elif action == "play":
        path = parts[1]
        res = alist_req("/api/fs/get", {"path": path})
        raw = res.get('data', {}).get('raw_url')
        if raw: await trigger_stream(update, raw, os.path.basename(path))
        else: await q.edit_message_text("❌ 无法获取直链")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(cb_handler))
    logger.info(f"Bot Started... Token: {'*' * 5}{BOT_TOKEN[-5:] if BOT_TOKEN else 'None'}")
    app.run_polling()