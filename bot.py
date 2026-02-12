import os
import sys
import logging
import requests
import json
import asyncio
import subprocess
import re
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 加载环境变量
load_dotenv()

# 配置信息
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")
ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244").rstrip('/')
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")
# 默认静态公网地址，如果有的话
ALIST_PUBLIC_URL_STATIC = os.getenv("ALIST_PUBLIC_URL", "").rstrip('/')

KEYS_FILE = "stream_keys.json"
CLOUDFLARED_BIN = "./cloudflared"

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.error("❌ 未找到 TG_BOT_TOKEN，请检查 .env 文件")
    sys.exit(1)

# 全局变量
alist_token = None
tunnel_process = None
current_public_url = None

# --- 辅助函数 ---

def load_keys():
    if not os.path.exists(KEYS_FILE): return {}
    try:
        with open(KEYS_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f: json.dump(keys, f)

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
    except Exception as e:
        logger.error(f"Alist 登录失败: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    url = f"{ALIST_HOST}{endpoint}"
    
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=10)
        else:
            res = requests.post(url, json=data, headers=headers, timeout=10)
            
        if res.status_code == 200 and res.json().get('code') == 401:
            headers["Authorization"] = get_alist_token()
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=10)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"code": 500, "message": str(e)}

async def add_offline_task(update, url):
    await update.message.reply_text("⏳ 正在提交 Aria2 离线任务...")
    # 尝试多种 API 路径以兼容不同版本的 Alist
    res = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [url], "tool": "aria2"})
    if res.get('code') != 200:
            res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [url], "tool": "aria2"})
    
    if res.get('code') == 200:
        await update.message.reply_text(f"✅ 任务已添加！\n文件将下载到根目录。")
    else:
        await update.message.reply_text(f"❌ 添加失败: {res.get('message')}")

# --- Cloudflare Tunnel 管理 ---

async def start_cloudflared():
    global tunnel_process, current_public_url
    
    if tunnel_process and tunnel_process.poll() is None:
        return current_public_url

    if not os.path.exists(CLOUDFLARED_BIN):
        return None

    try:
        # 清理旧日志
        if os.path.exists("tunnel.log"): os.remove("tunnel.log")

        # 启动 cloudflared tunnel
        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", "tunnel.log"]
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待日志文件生成并读取 URL
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

# --- GitHub Workflow ---

def trigger_github_workflow(file_url, target_rtmp):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失"
    
    public_base = get_effective_public_url()
    final_url = file_url
    
    # 将内网链接转换为公网链接
    if public_base:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            if final_url.startswith("http"):
                 final_url = final_url.replace(ALIST_HOST, public_base).replace("http://127.0.0.1:5244", public_base)
            else:
                 final_url = f"{public_base}{final_url}"
    else:
        if "127.0.0.1" in final_url or "localhost" in final_url:
            return False, "⚠️ 未开启远程访问 (隧道)，GitHub 无法连接内网文件。请先点击菜单中的 '🌐 开启/关闭 远程访问'。"

    logger.info(f"Stream URL: {final_url}")

    inputs = {"file_url": final_url, "rtmp_url": target_rtmp}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers, timeout=10)
        if res.status_code == 204:
            return True, "工作流已触发"
        else:
            return False, f"GitHub 错误 {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# --- 机器人处理函数 ---

async def start(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): 
        await update.message.reply_text("⛔️ 无权访问")
        return
    
    context.user_data.clear()
    
    # 重新设计键盘布局，增加 "(Magnet/HTTP)" 后缀，方便您确认是否更新成功
    keyboard = [
        ["📂 浏览云盘"],
        ["🧲 离线下载 (Magnet/HTTP)"],
        ["🌐 开启/关闭 远程访问", "🔐 查看登录信息"],
        ["🛑 停止推流", "🔑 密钥管理"]
    ]
    
    await update.message.reply_text(
        "👋 **StreamForge 控制台**\n\n"
        "👇 **请使用下方键盘操作**\n"
        "💡 提示：如果未看到键盘，请点击输入框右侧的图标，或输入 /menu 重试。\n"
        "📌 快捷方式：直接发送磁力链接给我也能下载。",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def download_command(update: Update, context):
    """专用下载命令处理"""
    if str(update.effective_user.id) != str(ADMIN_ID): return
    context.user_data['state'] = 'AWAITING_LINK'
    await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**", parse_mode='Markdown')

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    # 1. 优先处理直接发送的链接（快速离线下载）
    if msg.startswith("magnet:?") or (msg.startswith("http") and not context.user_data.get('state')):
        await add_offline_task(update, msg)
        return

    # 2. 处理状态机（手动点击按钮后的输入）
    state = context.user_data.get('state')
    if state == 'AWAITING_LINK':
        if msg == "/cancel":
            context.user_data.clear()
            await update.message.reply_text("已取消")
            await start(update, context)
            return
        await add_offline_task(update, msg)
        context.user_data['state'] = None
        return

    if state == 'AWAITING_KEY_NAME':
        context.user_data['new_key_name'] = msg
        context.user_data['state'] = 'AWAITING_KEY_URL'
        await update.message.reply_text(f"📝 名称: {msg}\n👉 请输入完整 RTMP 地址:")
        return
    
    if state == 'AWAITING_KEY_URL':
        name = context.user_data.get('new_key_name')
        keys = load_keys()
        keys[name] = msg
        save_keys(keys)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ 密钥 **{name}** 已保存", parse_mode='Markdown')
        return

    # 3. 处理菜单按钮
    if msg == "📂 浏览云盘":
        await update.message.reply_text("🔍 读取根目录...")
        await show_file_list(update, "/", 1)
        
    elif msg == "🧲 离线下载 (Magnet/HTTP)":
        context.user_data['state'] = 'AWAITING_LINK'
        await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**\n(或者直接粘贴链接给我，无需点此按钮)", parse_mode='Markdown')

    elif msg == "🌐 开启/关闭 远程访问":
        if current_public_url:
            stop_cloudflared()
            await update.message.reply_text("🚫 隧道已关闭。外网访问已停止。")
        else:
            msg_wait = await update.message.reply_text("⏳ 正在启动 Cloudflare 隧道 (需 5-10 秒)...")
            url = await start_cloudflared()
            if url:
                await msg_wait.edit_text(f"✅ **远程访问已开启**\n\n🔗 公网地址: `{url}`\n\n您现在可以在外网访问 Alist 管理页面。", parse_mode='Markdown')
            else:
                await msg_wait.edit_text("❌ 启动失败。请确保 setup.sh 已成功安装 cloudflared。")

    elif msg == "🔐 查看登录信息":
        url = get_effective_public_url() or ALIST_HOST
        status = " (内网)" if "127.0.0.1" in url else " (公网)"
        await update.message.reply_text(
            f"🔐 **Alist 登录凭证**{status}\n\n🔗 地址: `{url}`\n👤 用户: `{ALIST_USER}`\n🔑 密码: `{ALIST_PASSWORD}`",
            parse_mode='Markdown'
        )

    elif msg == "🔑 密钥管理":
        keys = load_keys()
        text = "🔑 **保存的推流地址**：\n"
        keyboard = []
        for k, v in keys.items():
            text += f"- {k}\n"
            keyboard.append([InlineKeyboardButton(f"🗑 删除 {k}", callback_data=f"delkey|{k}")])
        keyboard.append([InlineKeyboardButton("➕ 添加新地址", callback_data="addkey")])
        await update.message.reply_text(text or "暂无保存的地址", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif msg == "🛑 停止推流":
        await stop_workflow(update)
        
    elif msg == "⚙️ 系统状态":
        try:
            res = requests.get(f"{ALIST_HOST}/api/public/settings", timeout=2)
            alist_status = "✅ Alist 运行中" if res.status_code == 200 else "❌ Alist 未响应"
        except:
            alist_status = "❌ Alist 无法连接"
            
        tunnel_status = f"✅ 隧道开启 ({current_public_url})" if current_public_url else "⚪ 隧道关闭"
        
        await update.message.reply_text(f"🖥 **系统状态**:\n{alist_status}\n{tunnel_status}", parse_mode='Markdown')

async def show_file_list(update: Update, path, page):
    is_cb = bool(update.callback_query)
    message = update.callback_query.message if is_cb else update.message
    
    res = alist_api("/api/fs/list", data={"path": path, "page": page, "per_page": 10})
    if res.get('code') != 200:
        await message.reply_text(f"读取失败: {res.get('message')}")
        return

    content = res['data']['content'] or []
    total = res['data']['total']
    content.sort(key=lambda x: x['is_dir'], reverse=True)
    
    buttons = []
    if path != "/":
        parent = os.path.dirname(path.rstrip('/')) or "/"
        buttons.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"nav|{parent}|1")])
    
    for item in content:
        name = item['name']
        display_name = (name[:20] + '..') if len(name) > 20 else name
        full_path = f"{path.rstrip('/')}/{name}"
        
        if item['is_dir']:
            buttons.append([InlineKeyboardButton(f"📁 {display_name}", callback_data=f"nav|{full_path}|1")])
        else:
            buttons.append([InlineKeyboardButton(f"▶️ {display_name}", callback_data=f"pre_stream|{full_path}")])

    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav|{path}|{page-1}"))
    if page * 10 < total: nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"nav|{path}|{page+1}"))
    if nav_row: buttons.append(nav_row)

    markup = InlineKeyboardMarkup(buttons)
    text = f"📂 路径: `{path}`"
    if is_cb:
        await message.edit_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]

    if action == "nav":
        await show_file_list(update, data[1], int(data[2]))
    
    elif action == "pre_stream":
        path = data[1]
        context.user_data['pending_path'] = path
        keys = load_keys()
        btns = []
        if RTMP_URL:
            btns.append([InlineKeyboardButton("📡 默认地址 (.env)", callback_data="stream|default")])
        for k in keys:
            btns.append([InlineKeyboardButton(f"📡 {k}", callback_data=f"stream|{k}")])
        btns.append([InlineKeyboardButton("❌ 取消", callback_data="cancel")])
        
        await query.message.reply_text(f"🎬 准备推流: `{os.path.basename(path)}`\n请选择推流目标:", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif action == "stream":
        key_name = data[1]
        path = context.user_data.get('pending_path')
        if not path:
            await query.message.edit_text("❌ 操作已过期")
            return

        target_rtmp = RTMP_URL if key_name == "default" else load_keys().get(key_name)
        if not target_rtmp:
            await query.message.edit_text("❌ 无效的推流地址")
            return

        await query.message.edit_text(f"🔄 正在获取直链...\n文件: `{os.path.basename(path)}`", parse_mode='Markdown')
        
        # 获取直链
        res = alist_api("/api/fs/get", data={"path": path})
        raw_url = res.get('data', {}).get('raw_url')
        
        if not raw_url:
            await query.message.edit_text(f"❌ 无法获取文件直链: {res.get('message')}")
            return

        success, msg = trigger_github_workflow(raw_url, target_rtmp)
        icon = "✅" if success else "❌"
        await query.message.reply_text(f"{icon} 推流请求结果: {msg}")

    elif action == "addkey":
        context.user_data['state'] = 'AWAITING_KEY_NAME'
        await query.message.reply_text("⌨️ 请输入新推流地址的名称 (例如: Live1):")
        
    elif action == "delkey":
        keys = load_keys()
        if data[1] in keys:
            del keys[data[1]]
            save_keys(keys)
            await query.message.reply_text(f"🗑 已删除 {data[1]}")
    
    elif action == "cancel":
        await query.message.delete()

async def stop_workflow(update):
    msg = await update.message.reply_text("🛑 正在停止 GitHub 任务...")
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
        runs = requests.get(url, headers=headers).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                requests.post(f"{url[:-19]}/runs/{run['id']}/cancel", headers=headers)
                count += 1
        await msg.edit_text(f"✅ 已停止 {count} 个任务。")
    except Exception as e:
        await msg.edit_text(f"❌ 停止失败: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("download", download_command)) # 添加单独的命令
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 Bot 已启动！请在 Telegram 中发送 /start 更新菜单。")
    print("如果代码更新后菜单未变，请按 Ctrl+C 停止旧进程并重新运行 python bot.py")
    app.run_polling()
