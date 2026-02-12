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
  alistPublicUrl: "https://alist.glkk.dpdns.org",
  aria2Secret: "streamforge",
  cloudflaredToken: "eyJhIjoiMjEyOGViYjhlN2Y2OTU4MjZkNzVmNjkwZTBhZTE4MjEiLCJ0IjoiYTE3OTBhNmMtMWQyZi00MDUzLTlkOTktOGMyZWUyZmJlNTczIiwicyI6Ik1UTXpaamhsT1RVdE1tTTJaaTAwWmpnMUxXSXlaakF0WldWa1lUVXhaR0V3TlRnMCJ9",
  fileName: "movie.mp4",
  fileUrl: "",
  defaultCoverUrl: "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=1920&auto=format&fit=crop",
  videoBitrate: "6000k",
};

export const GITHUB_WORKFLOW_TEMPLATE = (config: StreamConfig) => `name: Alist Stream to Telegram

on:
  workflow_dispatch:
    inputs:
      file_url:
        description: 'Direct URL of the file'
        required: true
      rtmp_url:
        description: 'RTMP URL (including key)'
        required: true
      image_url:
        description: 'Background image for audio'
        required: false
        default: '${config.defaultCoverUrl}'

jobs:
  stream:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install FFmpeg
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg

      - name: Stream Process
        run: |
          FILE_URL="\${{ inputs.file_url }}"
          RTMP_URL="\${{ inputs.rtmp_url }}"
          COVER_URL="\${{ inputs.image_url }}"
          
          echo "Preparing stream for: $FILE_URL"
          
          if [[ "$FILE_URL" =~ \\.(mp3|flac|wav|m4a|aac|ogg)$ ]]; then
            echo "Audio detected. Using cover image."
            ffmpeg -re -loop 1 -i "$COVER_URL" -i "$FILE_URL" \
              -c:v libx264 -preset veryfast -tune stillimage \
              -c:a aac -b:a 192k -pix_fmt yuv420p -shortest \
              -f flv "$RTMP_URL"
          else
            echo "Video detected. Streaming directly."
            ffmpeg -re -i "$FILE_URL" \
              -c:v copy -c:a aac -strict experimental \
              -f flv "$RTMP_URL"
          fi
`;

export const GENERATE_ENV_CONTENT = (config: StreamConfig) => `TG_BOT_TOKEN=${config.telegramBotToken}
TG_ADMIN_ID=${config.telegramAdminId}
GITHUB_OWNER=${config.githubUser}
GITHUB_REPO=${config.githubRepo}
GITHUB_PAT=${config.githubPat}
RTMP_URL=${config.telegramRtmpUrl}${config.telegramStreamKey}
DEFAULT_COVER=${config.defaultCoverUrl}
ALIST_HOST=http://127.0.0.1:5244
ALIST_PUBLIC_URL=${config.alistPublicUrl}
ALIST_USER=admin
ALIST_PASSWORD=${config.alistPassword}
CLOUDFLARED_TOKEN=${config.cloudflaredToken}`;

export const PYTHON_BOT_SCRIPT = `import os
import sys
import logging
import requests
import subprocess
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 1. 加载配置 (修复路径问题)
# 获取当前脚本所在目录，确保 pm2 启动时能找到同目录下的 .env
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")

if os.path.exists(env_path):
    print(f"📝 Loading config from: {env_path}")
    load_dotenv(env_path)
else:
    print(f"⚠️ Warning: .env file not found at {env_path}, trying fallback locations...")
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
ALIST_PUBLIC_URL = os.getenv("ALIST_PUBLIC_URL")
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")

# 验证关键变量
if not BOT_TOKEN:
    print("❌ Fatal Error: TG_BOT_TOKEN not found in environment variables.")
    print("👉 Please edit .env file and set TG_BOT_TOKEN.")
    sys.exit(1)

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
            else:
                logger.error(f"Login Failed: {data}")
    except Exception as e:
        logger.error(f"Alist Login Error: {e}")
    return None

def alist_api(endpoint, method="POST", data=None):
    token = alist_token or get_alist_token()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        url = f"{ALIST_HOST}{endpoint}"
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=10)
        else:
            res = requests.post(url, json=data, headers=headers, timeout=10)
            
        if res.status_code == 200 and res.json().get('code') == 401:
             # Token失效重试
            headers["Authorization"] = get_alist_token()
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=10)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=10)
                
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

# --- 新增：管理功能函数 ---
def pm2_action(action, service):
    try:
        subprocess.run(["pm2", action, service], check=True)
        return True, f"{service} {action} 成功"
    except Exception as e:
        return False, str(e)

def get_system_status():
    try:
        # Check Alist Port
        try:
            requests.get(f"{ALIST_HOST}/api/public/settings", timeout=2)
            alist_status = "✅ 运行中"
        except:
            alist_status = "❌ 未响应"
            
        return f"🖥 **系统状态**\\n\\nAlist: {alist_status}"
    except Exception as e:
        return str(e)

# --- Bot Handlers ---

async def start(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    keyboard = [
        ["📂 浏览云盘", "⚙️ 系统管理"],
        ["🛑 停止推流"]
    ]
    await update.message.reply_text("👋 *StreamForge 控制台*\\n请选择操作：", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    # Main Menu
    if msg == "📂 浏览云盘": 
        await show_file_list(update, "/", 1)
    elif msg == "🛑 停止推流": 
        await stop_all_workflows(update)
    elif msg == "⚙️ 系统管理":
        keyboard = [
            ["🔄 重启 Alist", "📊 Alist 状态"],
            ["💾 存储列表", "🔙 返回主菜单"]
        ]
        await update.message.reply_text("⚙️ *系统管理面板*", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
    
    # System Menu
    elif msg == "🔙 返回主菜单":
        await start(update, context)
    elif msg == "🔄 重启 Alist":
        status_msg = await update.message.reply_text("⏳ 正在重启 Alist...")
        success, info = pm2_action("restart", "alist")
        await status_msg.edit_text(f"{'✅' if success else '❌'} {info}")
    elif msg == "📊 Alist 状态":
        info = get_system_status()
        await update.message.reply_text(info, parse_mode='Markdown')
    elif msg == "💾 存储列表":
        res = alist_api("/api/admin/storage/list", method="GET")
        if res.get('code') == 200:
            content = res['data']['content']
            text = "💾 *已挂载存储:*"
            for item in content:
                status = "🟢" if item['status'] == 'work' else "🔴"
                text += f"\\n{status} \`{item['mount_path']}\` ({item['driver']})"
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ 获取失败: {res.get('message', 'Unknown error')}")

    # Direct Link
    elif msg.startswith("http"):
        await update.message.reply_text("🔗 检测到外链，尝试推流...")
        success, info = trigger_github_workflow(msg, "DirectLink.mp4")
        await update.message.reply_text(f"{'✅' if success else '❌'} {info}")

async def show_file_list(obj, path, page):
    data = alist_api("/api/fs/list", method="POST", data={"path": path, "page": page, "per_page": 10})
    content = data.get('data', {}).get('content', [])
    total = data.get('data', {}).get('total', 0)
    
    if not content and path == "/":
        msg_text = "❌ Alist 列表为空，请检查挂载或配置。"
        if isinstance(obj, Update): await obj.message.reply_text(msg_text)
        else: await obj.callback_query.message.reply_text(msg_text)
        return

    content.sort(key=lambda x: x['is_dir'], reverse=True)
    buttons = []
    if path != "/":
        parent = os.path.dirname(path.rstrip('/')) or "/"
        buttons.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"nav|{parent}|1")])
    
    for item in content:
        name = item['name']
        fp = f"{path.rstrip('/')}/{name}"
        icon = "📁" if item['is_dir'] else "▶️"
        buttons.append([InlineKeyboardButton(f"{icon} {name}", callback_data=f"{'nav' if item['is_dir'] else 'play'}|{fp}|1")])
    
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav|{path}|{page-1}"))
    if page * 10 < total: nav.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"nav|{path}|{page+1}"))
    if nav: buttons.append(nav)
    
    markup = InlineKeyboardMarkup(buttons)
    text = f"📂 路径: \`{path}\`"
    if isinstance(obj, Update):
        await obj.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await obj.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    try:
        action, path, p_idx = query.data.split("|")
    except ValueError:
        return

    if action == "nav":
        await show_file_list(update, path, int(p_idx))
    elif action == "play":
        res = alist_api("/api/fs/get", method="POST", data={"path": path})
        raw = res.get('data', {}).get('raw_url')
        if raw:
            # Handle Localhost Replacement
            if ALIST_PUBLIC_URL and (raw.startswith("http://127.0.0.1") or raw.startswith("http://localhost")):
                # Remove the Alist host part and prepend public URL
                # NOTE: This assumes ALIST_PUBLIC_URL is configured correctly in .env
                # Simplistic replacement for standard Alist local proxy links
                raw = raw.replace(ALIST_HOST, ALIST_PUBLIC_URL).replace("http://127.0.0.1:5244", ALIST_PUBLIC_URL)

            await query.message.reply_text(f"🚀 启动推流: {os.path.basename(path)}")
            success, info = trigger_github_workflow(raw, path)
            await query.message.reply_text(f"{'✅' if success else '❌'} {info}")
        else:
            await query.message.reply_text("❌ 无法获取直链，请检查 Alist 权限")

async def stop_all_workflows(update):
    msg = await update.message.reply_text("🔍 正在请求停止 GitHub 任务...")
    headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    try:
        runs = requests.get(f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs?status=in_progress", headers=headers, timeout=10).json()
        count = 0
        for run in runs.get('workflow_runs', []):
            if run['name'] == 'Alist Stream to Telegram':
                requests.post(f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run['id']}/cancel", headers=headers, timeout=10)
                count += 1
        await msg.edit_text(f"🛑 已成功向 {count} 个工作流发送停止指令。")
    except Exception as e:
        await msg.edit_text(f"❌ 停止失败: {str(e)}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ 错误: 未找到 TG_BOT_TOKEN 环境变量")
        exit(1)
    
    print("🚀 正在初始化 Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("✅ Bot 已上线，按 Ctrl+C 停止")
    app.run_polling()
`;

export const GENERATE_SETUP_SCRIPT = (envContent: string, botContent: string) => `#!/bin/bash

echo "🚀 开始 StreamForge 环境智能部署..."

# 0. 自动生成配置文件
echo "📝 正在生成配置文件..."

# 写入 .env
cat << 'EOF' > .env
${envContent}
EOF
echo "✅ 已生成 .env"

# 写入 bot.py
cat << 'EOF' > bot.py
${botContent}
EOF
echo "✅ 已生成 bot.py"

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

# 3. 检查并安装 Cloudflared
echo "☁️ 检查 Cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    echo "📦 正在安装 Cloudflared..."
    pkg install cloudflared -y 2>/dev/null || {
        echo "⚠️ pkg install 失败，尝试启用 tur-repo..."
        pkg install tur-repo -y 2>/dev/null
        pkg install cloudflared -y 2>/dev/null || {
           echo "⚠️ 源安装失败，尝试下载二进制文件..."
           arch=$(uname -m)
           case $arch in
           aarch64) t="arm64" ;;
           x86_64) t="amd64" ;;
           *) t="arm64" ;;
           esac
           wget -O $PREFIX/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$t
           chmod +x $PREFIX/bin/cloudflared
        }
    }
else
    echo "✅ Cloudflared 已安装，跳过。"
fi

# 4. 检查 PM2 (Node.js 模块)
if ! command -v pm2 &> /dev/null; then
    echo "📦 正在安装 PM2 进程管理器..."
    npm install -g pm2
else
    echo "✅ PM2 已安装，跳过。"
fi

# 5. 检查并更新 Python 依赖
echo "📦 检查 Python 依赖库..."
pip install python-telegram-bot requests python-dotenv --upgrade

# 6. 配置 Alist
echo "⚙️ 配置 Alist 服务..."

# 先停止可能存在的实例
pm2 stop alist 2>/dev/null

# 强制重置 Alist 密码
echo "🔑 正在初始化 Alist 数据库并设置密码..."
if [ ! -f "data/data.db" ]; then
  timeout 5s alist server > /dev/null 2>&1
fi
alist admin set admin
echo "✅ Alist 管理员密码已重置为: admin"

# 读取环境变量中的 Cloudflared Token
source .env

# 验证关键配置是否为空
if [ -z "$TG_BOT_TOKEN" ]; then
    echo "⚠️  注意: 检测到 .env 文件中 TG_BOT_TOKEN 为空"
    echo "⚠️  脚本将继续执行，但在启动 bot 之前，请务必编辑 .env 文件填入 Token！"
    echo "⚠️  命令: nano .env"
fi

# 7. 启动服务 (使用 PM2)
echo "▶️ 启动服务..."
pm2 start alist --name alist -- server
pm2 start bot.py --name stream-bot --interpreter python

if [ -n "$CLOUDFLARED_TOKEN" ]; then
    echo "▶️ 启动 Cloudflared Tunnel (PM2 Managed)..."
    pm2 delete tunnel 2>/dev/null || true
    # Start Cloudflared with PM2.
    pm2 start cloudflared --name tunnel --restart-delay=3000 -- tunnel run --token "$CLOUDFLARED_TOKEN"
fi

# 8. 保存 PM2 状态以实现持久化
echo "💾 保存当前进程状态..."
pm2 save

# 9. 配置 Termux 启动时自动恢复
echo "🔌 配置开机(打开App)自启动..."
if ! grep -q "pm2 resurrect" ~/.bashrc; then
    echo "# StreamForge Auto Start" >> ~/.bashrc
    echo "pm2 resurrect > /dev/null 2>&1" >> ~/.bashrc
    echo "✅ 已添加自动恢复到 .bashrc"
else
    echo "✅ 自启动配置已存在。"
fi

echo ""
echo "🎉 部署脚本执行完毕！"
echo "--------------------------------"
echo "📊 当前运行状态:"
pm2 status
echo "--------------------------------"
echo "💡 提示:"
echo "- 机器人: /start"
echo "- Alist: http://127.0.0.1:5244 (Local)"
if [ -n "$ALIST_PUBLIC_URL" ]; then
    echo "- Public: $ALIST_PUBLIC_URL"
fi
echo "👉 如果 Bot 状态为 error，请检查 .env 配置并重启: pm2 restart stream-bot"
echo "--------------------------------"
`;