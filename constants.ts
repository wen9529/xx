import { StreamConfig } from "./types";

export const DEFAULT_STREAM_CONFIG: StreamConfig = {
  githubUser: "your-username",
  githubRepo: "stream-repo",
  githubPat: "",
  telegramBotToken: "",
  telegramAdminId: "",
  telegramRtmpUrl: "rtmp://x.rtmp.t.me/s/",
  telegramStreamKey: "",
  alistPassword: "admin",
  aria2Secret: "streamforge",
  fileName: "movie.mp4",
  fileUrl: "",
  defaultCoverUrl: "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=1920&auto=format&fit=crop",
  videoBitrate: "6000k",
};

export const GENERATE_ENV_CONTENT = (config: StreamConfig) => `TG_BOT_TOKEN=${config.telegramBotToken}
TG_ADMIN_ID=${config.telegramAdminId}
GITHUB_OWNER=${config.githubUser}
GITHUB_REPO=${config.githubRepo}
GITHUB_PAT=${config.githubPat}
RTMP_URL=${config.telegramRtmpUrl}${config.telegramStreamKey}
DEFAULT_COVER=${config.defaultCoverUrl}
ALIST_HOST=http://127.0.0.1:5244
ALIST_USER=admin
ALIST_PASSWORD=${config.alistPassword}`;

export const SETUP_SCRIPT_CONTENT = `#!/bin/bash

echo "🚀 开始 StreamForge 环境智能部署..."

# 函数：检查并安装软件包
check_install() {
    if ! command -v $1 &> /dev/null; then
        echo "📦 正在安装 $2..."
        pkg install -y $2
    else
        echo "✅ $1 已安装，跳过。"
    fi
}

# 1. 更新软件源
echo "🔄 正在同步软件源..."
pkg update -y

# 2. 检查基础软件包
check_install python python
check_install alist alist
check_install ffmpeg ffmpeg
check_install git git
check_install node nodejs

# 3. 检查 PM2 (Node.js 模块)
if ! command -v pm2 &> /dev/null; then
    echo "📦 正在安装 PM2 进程管理器..."
    npm install -g pm2
else
    echo "✅ PM2 已安装，跳过。"
fi

# 4. 检查并更新 Python 依赖
echo "📦 检查 Python 依赖库 (telegram, requests, dotenv)..."
pip install python-telegram-bot requests python-dotenv --upgrade

# 5. 配置并启动服务 (使用 PM2)
echo "⚙️ 配置服务自动化..."

# 停止并删除旧的 PM2 任务以免重复
pm2 delete alist stream-bot 2>/dev/null

# 启动 Alist
echo "▶️ 启动 Alist 服务..."
pm2 start alist --name alist -- server

# 启动 Bot
if [ -f "bot.py" ]; then
    echo "▶️ 启动 Telegram Bot..."
    pm2 start bot.py --name stream-bot --interpreter python
else
    echo "❌ 错误: 未在当前目录找到 bot.py 文件！"
    echo "请先确保 bot.py 内容已正确保存到本地。"
fi

# 6. 保存 PM2 状态以实现持久化
pm2 save

echo ""
echo "🎉 部署脚本执行完毕！"
echo "--------------------------------"
echo "📊 当前运行状态:"
pm2 status
echo "--------------------------------"
echo "💡 提示:"
echo "- 查看日志: pm2 logs stream-bot"
echo "- 重启 Bot: pm2 restart stream-bot"
echo "- Alist 地址: http://127.0.0.1:5244"
echo "--------------------------------"
`;

export const PYTHON_BOT_SCRIPT = `import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 1. 加载配置
load_dotenv(".env")
home_env = os.path.expanduser("~/.env")
if os.path.exists(home_env):
    load_dotenv(home_env)

# 2. 获取环境变量
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")
DEFAULT_COVER = os.getenv("DEFAULT_COVER")
ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244")
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")

# 3. 日志配置
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

alist_token = None

def get_alist_token():
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
    except Exception as e:
        logger.error(f"Alist Login Error: {e}")
    return None

def alist_api(endpoint, data=None):
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        res = requests.post(f"{ALIST_HOST}{endpoint}", json=data, headers=headers, timeout=10)
        if res.json().get('code') == 401:
            headers["Authorization"] = get_alist_token()
            res = requests.post(f"{ALIST_HOST}{endpoint}", json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {}

def trigger_github_workflow(file_url, file_name):
    if not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_PAT]):
        return False, "GitHub 配置缺失"
    
    inputs = {"file_url": file_url, "rtmp_url": RTMP_URL}
    ext = file_name.split('.')[-1].lower()
    mode = "🎬 视频模式"
    if ext in ['mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']:
        inputs["image_url"] = DEFAULT_COVER
        mode = "🎵 音频模式"

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers, timeout=15)
        return res.status_code == 204, mode
    except Exception as e:
        return False, str(e)

async def start(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    keyboard = [["📂 浏览云盘", "🛑 停止任务"]]
    await update.message.reply_text("👋 *StreamForge 控制台*\\n请选择操作：", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    if msg == "📂 浏览云盘": await show_file_list(update, "/", 1)
    elif msg == "🛑 停止任务": await stop_all_workflows(update)
    elif msg.startswith("http"):
        success, info = trigger_github_workflow(msg, "Link.mp4")
        await update.message.reply_text(f"{'✅' if success else '❌'} {info}")

async def show_file_list(obj, path, page):
    data = alist_api("/api/fs/list", {"path": path, "page": page, "per_page": 10})
    content = data.get('data', {}).get('content', [])
    total = data.get('data', {}).get('total', 0)
    content.sort(key=lambda x: x['is_dir'], reverse=True)
    buttons = []
    if path != "/":
        parent = os.path.dirname(path.rstrip('/')) or "/"
        buttons.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"nav|{parent}|1")])
    for item in content:
        name, fp = item['name'], f"{path.rstrip('/')}/{item['name']}"
        icon = "📁" if item['is_dir'] else "▶️"
        buttons.append([InlineKeyboardButton(f"{icon} {name}", callback_data=f"{'nav' if item['is_dir'] else 'play'}|{fp}|1")])
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav|{path}|{page-1}"))
    if page * 10 < total: nav.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"nav|{path}|{page+1}"))
    if nav: buttons.append(nav)
    markup = InlineKeyboardMarkup(buttons)
    text = f"📂 路径: \`{path}\`"
    if isinstance(obj, Update): await obj.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    else: await obj.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    action, path, p_idx = query.data.split("|")
    if action == "nav": await show_file_list(update, path, int(p_idx))
    elif action == "play":
        res = alist_api("/api/fs/get", {"path": path})
        raw = res.get('data', {}).get('raw_url')
        if raw:
            success, info = trigger_github_workflow(raw, path)
            await query.message.reply_text(f"{'✅' if success else '❌'} {info}\\n{os.path.basename(path)}")
        else: await query.message.reply_text("❌ 获取直链失败")

async def stop_all_workflows(update):
    msg = await update.message.reply_text("🔍 正在停止任务...")
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        runs = requests.get(f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress", headers=headers, timeout=10).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                requests.post(f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run['id']}/cancel", headers=headers, timeout=10)
                count += 1
        await msg.edit_text(f"🛑 已停止 {count} 个工作流")
    except Exception as e:
        await msg.edit_text(f"❌ 失败: {str(e)}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ 未设置 TG_BOT_TOKEN")
        exit(1)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 Bot Started")
    app.run_polling()
`;

export const GITHUB_WORKFLOW_TEMPLATE = (config: StreamConfig) => `name: Alist Stream to Telegram

on:
  workflow_dispatch:
    inputs:
      file_url:
        description: 'Media URL (Video or Audio)'
        required: true
      image_url:
        description: 'Cover Image URL (For Audio Mode)'
        required: false
      rtmp_url:
        description: 'RTMP URL'
        required: true

jobs:
  stream:
    runs-on: ubuntu-latest
    timeout-minutes: 360 # 6 Hours Max
    steps:
      - uses: actions/checkout@v3
      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg
      
      - name: Stream to Telegram
        run: |
          FILE_URL="\${{ github.event.inputs.file_url }}"
          IMAGE_URL="\${{ github.event.inputs.image_url }}"
          RTMP_URL="\${{ github.event.inputs.rtmp_url }}"
          
          if [ -n "$IMAGE_URL" ]; then
            ffmpeg -re -loop 1 -framerate 30 -i "$IMAGE_URL" -i "$FILE_URL" \\
              -c:v libx264 -preset medium -tune stillimage -b:v 4000k -maxrate 4000k -bufsize 8000k \\
              -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \\
              -c:a aac -b:a 320k -ar 48000 -ac 2 \\
              -shortest -f flv "$RTMP_URL"
          else
            ffmpeg -re -i "$FILE_URL" \\
              -c:v libx264 -preset medium -b:v ${config.videoBitrate} -maxrate ${config.videoBitrate} -bufsize 12000k \\
              -vf "scale=1920:-2:flags=lanczos" -pix_fmt yuv420p -g 60 \\
              -c:a aac -b:a 320k -ar 48000 -ac 2 \\
              -f flv "$RTMP_URL"
          fi
`;
