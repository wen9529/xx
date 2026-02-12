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

echo "🚀 开始 StreamForge 环境部署..."

# 1. 更新 Termux 源并安装基础包
echo "📦 正在更新软件源并安装依赖 (Python, Alist, FFmpeg, Node.js)..."
pkg update -y
pkg install -y python alist ffmpeg git nodejs

# 2. 安装 PM2 (用于后台进程管理)
echo "📦 正在安装 PM2..."
npm install -g pm2

# 3. 安装 Python 依赖库
echo "📦 正在安装 Python 库 (Telegram Bot, Requests)..."
pip install python-telegram-bot requests python-dotenv

# 4. 启动 Alist (如果尚未运行)
echo "⚙️ 启动 Alist 服务..."
# 使用 PM2 管理 Alist，避免后台被杀
pm2 start alist --name alist -- server

# 5. 启动 Telegram Bot
echo "🤖 启动 Bot..."
# 确保 bot.py 存在
if [ -f "bot.py" ]; then
    pm2 start bot.py --name stream-bot --interpreter python
    echo "✅ Bot 已通过 PM2 启动"
else
    echo "⚠️ 未找到 bot.py，请确保文件已保存，然后手动运行: pm2 start bot.py --interpreter python"
fi

# 6. 保存 PM2 状态 (开机自启)
pm2 save

echo "🎉 部署完成！"
echo "👉 Alist 地址: http://127.0.0.1:5244 (默认密码请查看 Alist 文档或终端输出)"
echo "👉 Bot 状态: 使用 'pm2 status' 查看"
`;

export const PYTHON_BOT_SCRIPT = `import os
import logging
import requests
import mimetypes
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 1. 加载配置
home_dir = os.path.expanduser("~")
load_dotenv(os.path.join(home_dir, ".env"))

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

# --- 核心函数 ---

def get_alist_token():
    """获取 Alist Token"""
    global alist_token
    try:
        url = f"{ALIST_HOST}/api/auth/login"
        res = requests.post(url, json={"username": ALIST_USER, "password": ALIST_PASSWORD})
        if res.status_code == 200:
            data = res.json()
            if data.get('code') == 200:
                alist_token = data['data']['token']
                return alist_token
    except Exception as e:
        logger.error(f"Alist Login Error: {e}")
    return None

def alist_api(endpoint, data=None):
    """通用 Alist API 请求"""
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        res = requests.post(f"{ALIST_HOST}{endpoint}", json=data, headers=headers)
        # 如果 Token 失效 (401)，重新获取并重试
        if res.json().get('code') == 401:
            headers["Authorization"] = get_alist_token()
            res = requests.post(f"{ALIST_HOST}{endpoint}", json=data, headers=headers)
        return res.json()
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {}

def trigger_github_workflow(file_url, file_name):
    """触发 GitHub Action 推流"""
    inputs = {
        "file_url": file_url,
        "rtmp_url": RTMP_URL
    }
    
    # 简单的文件类型判断
    ext = file_name.split('.')[-1].lower()
    if ext in ['mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']:
        inputs["image_url"] = DEFAULT_COVER # 音频模式需要封面
        mode = "🎵 音频模式"
    else:
        mode = "🎬 视频模式"

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    try:
        res = requests.post(url, json={"ref": "main", "inputs": inputs}, headers=headers)
        return res.status_code == 204, mode
    except Exception as e:
        return False, str(e)

# --- Bot 交互逻辑 ---

async def start(update: Update, context):
    """/start 命令"""
    if str(update.effective_user.id) != str(ADMIN_ID): return
    
    keyboard = [["📂 浏览云盘", "🛑 停止任务"]]
    await update.message.reply_text(
        "👋 *StreamForge 控制台*\\n请选择操作：",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def menu_handler(update: Update, context):
    """处理菜单按钮"""
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    if msg == "📂 浏览云盘":
        await show_file_list(update, "/", 1)
    elif msg == "🛑 停止任务":
        await stop_all_workflows(update)
    else:
        # 允许直接发送直链
        if msg.startswith("http"):
            await update.message.reply_text("🔗 检测到链接，尝试推流...")
            success, info = trigger_github_workflow(msg, "DirectLink.mp4")
            if success:
                await update.message.reply_text(f"✅ 推流请求已发送 ({info})")
            else:
                await update.message.reply_text(f"❌ 请求失败: {info}")

async def show_file_list(obj, path, page):
    """显示 Alist 文件列表 (支持翻页)"""
    data = alist_api("/api/fs/list", {"path": path, "page": page, "per_page": 10})
    content = data.get('data', {}).get('content', [])
    total = data.get('data', {}).get('total', 0)
    
    # 排序：文件夹在前
    content.sort(key=lambda x: x['is_dir'], reverse=True)
    
    buttons = []
    # 返回上级按钮
    if path != "/":
        parent_dir = os.path.dirname(path.rstrip('/')) or "/"
        buttons.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"nav|{parent_dir}|1")])
    
    for item in content:
        name = item['name']
        full_path = f"{path.rstrip('/')}/{name}"
        
        if item['is_dir']:
            buttons.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"nav|{full_path}|1")])
        else:
            # 文件点击即推流
            buttons.append([InlineKeyboardButton(f"▶️ {name}", callback_data=f"play|{full_path}")])

    # 翻页按钮
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav|{path}|{page-1}"))
    if page * 10 < total:
        nav_row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"nav|{path}|{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    markup = InlineKeyboardMarkup(buttons)
    text_content = f"📂 路径: \`{path}\`"
    
    if isinstance(obj, Update):
        await obj.message.reply_text(text_content, reply_markup=markup, parse_mode='Markdown')
    else:
        await obj.callback_query.edit_message_text(text_content, reply_markup=markup, parse_mode='Markdown')

async def callback_handler(update: Update, context):
    """处理按钮点击"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("|", 2)
    action = parts[0]
    path = parts[1]
    
    if action == "nav":
        page = int(parts[2])
        await show_file_list(update, path, page)
        
    elif action == "play":
        # 获取文件直链
        res = alist_api("/api/fs/get", {"path": path})
        raw_url = res.get('data', {}).get('raw_url')
        
        if raw_url:
            await query.message.reply_text(f"🚀 正在获取直链并启动推流...\\n📄 文件: {os.path.basename(path)}")
            success, info = trigger_github_workflow(raw_url, path)
            if success:
                await query.message.reply_text(f"✅ 成功! {info}\\nGitHub Action 已触发。")
            else:
                await query.message.reply_text(f"❌ 失败: {info}")
        else:
            await query.message.reply_text("❌ 无法获取文件直链 (raw_url)")

async def stop_all_workflows(update):
    """停止所有正在运行的 GitHub Action"""
    msg = await update.message.reply_text("🔍 正在扫描运行中的任务...")
    
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # 获取运行中的工作流
    list_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress"
    runs = requests.get(list_url, headers=headers).json()
    
    count = 0
    if 'workflow_runs' in runs:
        for run in runs['workflow_runs']:
            if run['name'] == 'Alist Stream to Telegram':
                cancel_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run['id']}/cancel"
                requests.post(cancel_url, headers=headers)
                count += 1
                
    await msg.edit_text(f"🛑 已发送取消指令给 {count} 个任务。")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ 错误: 未找到 TG_BOT_TOKEN 环境变量")
        exit(1)
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("✅ Bot 已启动...")
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
          
          # High Quality Audio Settings: AAC 320k 48kHz
          # High Quality Video Settings: ${config.videoBitrate} bitrate, Medium Preset, 1080p
          
          if [ -n "$IMAGE_URL" ]; then
            echo "🎵 Audio + Image Mode Detected"
            echo "Audio: $FILE_URL"
            echo "Image: $IMAGE_URL"
            
            # -loop 1: Loop the image
            # -framerate 30: Create 30fps video
            # -shortest: End stream when audio ends
            # -tune stillimage: Optimize encoding for static image
            
            ffmpeg -re \
              -loop 1 -framerate 30 -i "$IMAGE_URL" \
              -i "$FILE_URL" \
              -c:v libx264 -preset medium -tune stillimage -b:v 4000k -maxrate 4000k -bufsize 8000k \
              -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \
              -c:a aac -b:a 320k -ar 48000 -ac 2 \
              -shortest \
              -f flv "$RTMP_URL"
              
          else
            echo "🎬 Video Mode Detected"
            echo "Video: $FILE_URL"
            
            # -reconnect flags: Robustness against network drops
            # -preset medium: Better quality than veryfast
            # -profile:v high: High profile for better quality
            
            ffmpeg -re \
              -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 \
              -i "$FILE_URL" \
              -c:v libx264 -preset medium -profile:v high -level 4.1 \
              -b:v ${config.videoBitrate} -maxrate ${config.videoBitrate} -bufsize 12000k \
              -vf "scale=1920:-2:flags=lanczos" \
              -pix_fmt yuv420p -g 60 \
              -c:a aac -b:a 320k -ar 48000 -ac 2 \
              -f flv "$RTMP_URL"
          fi
`;
