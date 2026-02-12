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

# --- Cloudflare Tunnel 管理 ---

async def start_cloudflared():
    global tunnel_process, current_public_url
    
    if tunnel_process and tunnel_process.poll() is None:
        return current_public_url

    if not os.path.exists(CLOUDFLARED_BIN):
        return None

    try:
        # 启动 cloudflared tunnel
        # 使用 metrics server 避免 log 解析的复杂性，或者直接解析 stderr
        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", ALIST_HOST, "--logfile", "tunnel.log"]
        tunnel_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待日志文件生成并读取 URL
        for i in range(20):
            await asyncio.sleep(1)
            if os.path.exists("tunnel.log"):
                with open("tunnel.log", "r") as f:
                    content = f.read()
                    # 匹配 trycloudflare.com 的 URL
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                    if match:
                        current_public_url = match.group(0)
                        return current_public_url
        
        # 超时未获取到
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
    # 清理日志
    if os.path.exists("tunnel.log"):
        os.remove("tunnel.log")

def get_effective_public_url():
    """获取当前有效的公网地址（优先使用隧道，其次配置的静态地址）"""
    if current_public_url:
        return current_public_url
    return ALIST_PUBLIC_URL_STATIC

# --- GitHub Workflow ---

def trigger_github_workflow(file_url, target_rtmp):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失"
    
    # 动态替换为公网地址
    public_base = get_effective_public_url()
    final_url = file_url
    
    if public_base:
        # 如果原始 URL 是内网 IP，进行替换
        if "127.0.0.1" in final_url or "localhost" in final_url:
            # 移除内网部分，拼接公网部分
            # 假设 Alist 返回的是 http://127.0.0.1:5244/d/local/...
            # 或者是相对路径 /d/local/...
            if final_url.startswith("http"):
                 # 简单粗暴替换 host
                 final_url = final_url.replace(ALIST_HOST, public_base).replace("http://127.0.0.1:5244", public_base)
            else:
                 final_url = f"{public_base}{final_url}"
    else:
        # 如果没有公网地址，且 URL 是内网的，GitHub Actions 将无法访问
        if "127.0.0.1" in final_url or "localhost" in final_url:
            return False, "⚠️ 错误：未开启公网访问 (隧道)，GitHub 无法下载内网文件。请先点击'🌐 开启远程访问'。"

    logger.info(f"提交给 GitHub 的文件流地址: {final_url}")

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
    keyboard = [
        ["📂 浏览云盘", "🧲 离线下载"],
        ["🌐 远程访问", "🔑 密钥管理"],
        ["🛑 停止推流", "⚙️ 系统状态"]
    ]
    await update.message.reply_text(
        "👋 **StreamForge 控制台**\n请选择操作：",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    # 状态机：处理离线下载链接输入
    state = context.user_data.get('state')
    if state == 'AWAITING_LINK':
        if msg == "/cancel":
            context.user_data.clear()
            await update.message.reply_text("已取消")
            await start(update, context)
            return
        
        await update.message.reply_text("⏳ 正在提交 Aria2 任务...")
        res = alist_api("/api/fs/offline/add", data={"path": "/", "urls": [msg], "tool": "aria2"})
        if res.get('code') != 200:
             res = alist_api("/api/fs/add_offline_download", data={"paths": ["/"], "urls": [msg], "tool": "aria2"})
        
        if res.get('code') == 200:
            await update.message.reply_text("✅ 离线任务添加成功！")
        else:
            await update.message.reply_text(f"❌ 添加失败: {res.get('message')}")
        
        context.user_data['state'] = None
        return

    # 状态机：处理添加密钥
    if state == 'AWAITING_KEY_NAME':
        context.user_data['new_key_name'] = msg
        context.user_data['state'] = 'AWAITING_KEY_URL'
        await update.message.reply_text(f"📝 名称: {msg}\n👉 请输入完整 RTMP 地址 (包含密钥):")
        return
    
    if state == 'AWAITING_KEY_URL':
        name = context.user_data.get('new_key_name')
        keys = load_keys()
        keys[name] = msg
        save_keys(keys)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ 密钥 **{name}** 已保存", parse_mode='Markdown')
        return

    # 主菜单命令
    if msg == "📂 浏览云盘":
        await update.message.reply_text("🔍 读取根目录...")
        await show_file_list(update, "/", 1)
        
    elif msg == "🧲 离线下载":
        context.user_data['state'] = 'AWAITING_LINK'
        await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**\n发送 /cancel 取消", parse_mode='Markdown')

    elif msg == "🌐 远程访问":
        keyboard = [
            [InlineKeyboardButton("🚀 开启/刷新 隧道", callback_data="tunnel_start")],
            [InlineKeyboardButton("⛔ 关闭 隧道", callback_data="tunnel_stop")],
            [InlineKeyboardButton("📋 查看登录信息", callback_data="show_login")]
        ]
        
        status_text = "Checking..."
        if current_public_url:
            status_text = f"🟢 **在线**\n🔗 地址: `{current_public_url}`"
        elif ALIST_PUBLIC_URL_STATIC:
             status_text = f"🔵 **静态配置**\n🔗 地址: `{ALIST_PUBLIC_URL_STATIC}`"
        else:
            status_text = "🔴 **未开启** (外网无法访问)"

        await update.message.reply_text(f"🌐 **公网访问状态**:\n{status_text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
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
            alist_status = "✅ Alist 在线" if res.status_code == 200 else "❌ Alist 异常"
        except:
            alist_status = "❌ 无法连接 Alist"
            
        tunnel_status = "✅ 隧道开启" if current_public_url else "⚪ 隧道关闭"
        
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
    
    elif action == "tunnel_start":
        await query.message.edit_text("⏳ 正在启动 Cloudflare 隧道，请稍候...")
        url = await start_cloudflared()
        if url:
            await query.message.edit_text(f"✅ **隧道已建立**\n\n🔗 公网地址: `{url}`\n\n⚠️ 此地址为临时地址，重启脚本后会改变。", parse_mode='Markdown')
        else:
            await query.message.edit_text("❌ 启动失败。请检查是否已运行 setup.sh 安装 cloudflared，或查看日志。")
            
    elif action == "tunnel_stop":
        stop_cloudflared()
        await query.message.edit_text("🚫 隧道已关闭。外网将无法访问。", parse_mode='Markdown')

    elif action == "show_login":
        url = get_effective_public_url() or ALIST_HOST
        await query.message.reply_text(
            f"🔐 **Alist 登录信息**\n\n地址: `{url}`\n用户: `{ALIST_USER}`\n密码: `{ALIST_PASSWORD}`",
            parse_mode='Markdown'
        )

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

        # 触发 GitHub Workflow
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
    msg = await update.message.reply_text("🛑 正在尝试停止 GitHub 任务...")
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
        runs = requests.get(url, headers=headers).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                requests.post(f"{url[:-19]}/runs/{run['id']}/cancel", headers=headers)
                count += 1
        await msg.edit_text(f"✅ 已发送停止指令给 {count} 个正在运行的任务。")
    except Exception as e:
        await msg.edit_text(f"❌ 停止失败: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🤖 Bot is running...")
    app.run_polling()
