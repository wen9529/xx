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
  aria2Secret: "streamforge_secret", // Default simple secret
  fileName: "movie.mp4",
  fileUrl: "",
};

// .env File Template
export const ENV_FILE_TEMPLATE = (config: StreamConfig) => `TG_BOT_TOKEN=${config.telegramBotToken}
TG_ADMIN_ID=${config.telegramAdminId}
GITHUB_OWNER=${config.githubUser}
GITHUB_REPO=${config.githubRepo}
GITHUB_PAT=${config.githubPat}
RTMP_URL=${config.telegramRtmpUrl}
ALIST_HOST=http://127.0.0.1:5244
ALIST_USER=admin
ALIST_PASSWORD=${config.alistPassword}`;

// 1. Termux One-Click Setup Script
export const TERMUX_SETUP_SCRIPT = (config: StreamConfig) => `#!/bin/bash

# StreamForge - Intelligent Termux Deployment Script
# Features: Smart Dependency Check, PM2 Process Management, Alist & Aria2 Setup

# Colors
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
RED='\\033[0;31m'
NC='\\033[0m' # No Color

function log_info() { echo -e "\${BLUE}[INFO]\${NC} $1"; }
function log_success() { echo -e "\${GREEN}[SUCCESS]\${NC} $1"; }
function log_warn() { echo -e "\${YELLOW}[SKIP]\${NC} $1"; }
function log_error() { echo -e "\${RED}[ERROR]\${NC} $1"; }

# --- 1. Smart Dependency Check Function ---
function check_and_install() {
    PACKAGE=$1
    CMD=$2
    
    if command -v $CMD >/dev/null 2>&1; then
        log_warn "$PACKAGE is already installed ($CMD found)."
    else
        log_info "Installing $PACKAGE..."
        pkg install -y $PACKAGE
        
        # Verify installation
        if ! command -v $CMD >/dev/null 2>&1; then
             log_error "Failed to install $PACKAGE. Please check your internet or repo."
             exit 1
        fi
    fi
}

echo "🚀 Starting StreamForge Intelligent Deployment..."

# --- 2. System Updates & Core Packages ---
log_info "Updating package lists..."
pkg update -y 

# Install Core Tools
check_and_install "git" "git"
check_and_install "python" "python"
check_and_install "alist" "alist"
check_and_install "aria2" "aria2c"
check_and_install "nodejs" "node" # Required for PM2

# --- 3. Install PM2 (Process Manager) ---
if command -v pm2 >/dev/null 2>&1; then
    log_warn "PM2 is already installed."
else
    log_info "Installing PM2 via npm..."
    npm install -g pm2
fi

# --- 4. Python Dependencies ---
# Pip handles "Requirement already satisfied" internally, so we just run it.
log_info "Checking Python libraries..."
pip install python-telegram-bot requests python-dotenv

# --- 5. Configuration (Secrets) ---
log_info "Generating configuration..."
cat << EOF > .env
TG_BOT_TOKEN=${config.telegramBotToken}
TG_ADMIN_ID=${config.telegramAdminId}
GITHUB_OWNER=${config.githubUser}
GITHUB_REPO=${config.githubRepo}
GITHUB_PAT=${config.githubPat}
RTMP_URL=${config.telegramRtmpUrl}
ALIST_HOST=http://127.0.0.1:5244
ALIST_USER=admin
ALIST_PASSWORD=${config.alistPassword}
EOF

# --- 6. Service Setup & PM2 Startup ---
log_info "Configuring Services with PM2..."

# Stop specific processes to ensure clean slate (safer than delete all)
pm2 delete aria2 >/dev/null 2>&1 || true
pm2 delete alist >/dev/null 2>&1 || true
pm2 delete stream-bot >/dev/null 2>&1 || true

# 6.1 Setup Aria2
touch aria2.session
# Create a small startup script for Aria2 to avoid CLI argument parsing issues in PM2
echo "aria2c --enable-rpc --rpc-listen-all=false --rpc-secret=${config.aria2Secret} --daemon=false --save-session=aria2.session --input-file=aria2.session" > start_aria2.sh
chmod +x start_aria2.sh
pm2 start ./start_aria2.sh --name aria2

# 6.2 Setup Alist
# Reset password first
log_info "Setting Alist admin password..."
if command -v alist >/dev/null 2>&1; then
  alist admin set ${config.alistPassword}
else
  # Fallback if binary is local
  ./alist admin set ${config.alistPassword}
fi

# Start Alist via PM2
pm2 start alist --name alist -- server

# 6.3 Setup Telegram Bot
pm2 start bot.py --name stream-bot --interpreter python

# --- 7. Finalize ---
pm2 save
log_success "Deployment Complete!"
echo ""
echo -e "\${GREEN}📊 PM2 Process List:\${NC}"
pm2 list
echo ""
echo "⚠️  IMPORTANT: Go to Alist Web UI (http://localhost:5244) -> Settings -> Global -> Aria2"
echo "    Set RPC Url: http://localhost:6800/jsonrpc"
echo "    Set RPC Secret: ${config.aria2Secret}"
echo ""
echo "Type 'pm2 log' to see bot logs."
echo "Type 'pm2 monit' to monitor processes."
`;

// 2. Python Telegram Bot Script
export const PYTHON_BOT_SCRIPT = `import os
import logging
import requests
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Load env
load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = int(os.getenv("TG_ADMIN_ID") or 0)
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")

# Alist Config
ALIST_HOST = os.getenv("ALIST_HOST", "http://127.0.0.1:5244")
ALIST_USER = os.getenv("ALIST_USER", "admin")
ALIST_PASSWORD = os.getenv("ALIST_PASSWORD", "admin")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

alist_token = None

def get_alist_token():
    global alist_token
    url = f"{ALIST_HOST}/api/auth/login"
    try:
        data = {"username": ALIST_USER, "password": ALIST_PASSWORD}
        res = requests.post(url, json=data)
        if res.status_code == 200:
            alist_token = res.json().get('data', {}).get('token')
            return alist_token
    except Exception as e:
        logger.error(f"Alist Login Error: {e}")
    return None

def alist_api_call(endpoint, method="POST", data=None):
    global alist_token
    if not alist_token:
        get_alist_token()
    
    url = f"{ALIST_HOST}{endpoint}"
    headers = {"Authorization": alist_token, "Content-Type": "application/json"}
    
    try:
        if method == "POST":
            res = requests.post(url, json=data, headers=headers)
        else:
            res = requests.get(url, headers=headers)
            
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logger.error(f"API Error {endpoint}: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "👋 StreamForge Bot Ready! (PM2 Managed)\\n\\n"
        "📥 *Download:*\\n"
        "/download <url> - Offline download to Alist\\n\\n"
        "📂 *Manage:*\\n"
        "/ls - Browse files & Stream",
        parse_mode="Markdown"
    )

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if not context.args:
        await update.message.reply_text("Usage: /download <http_url> [path]")
        return

    url = context.args[0]
    # Default path is root '/', can be changed
    path = context.args[1] if len(context.args) > 1 else "/"
    
    # Alist Offline Download API
    # tool: 'aria2', path: save path, urls: list of urls
    payload = {
        "method": "aria2",
        "path": path,
        "urls": [url]
    }
    
    res = alist_api_call("/api/fs/add_offline_download", data=payload)
    
    if res and res.get('code') == 200:
        await update.message.reply_text(f"✅ Task added to Aria2!\\nTarget: {path}")
    else:
        msg = res.get('message') if res else "Unknown error"
        await update.message.reply_text(f"❌ Failed to add task.\\nError: {msg}\\n\\n(Did you configure Aria2 in Alist settings?)")

async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await show_file_list(update, "/")

async def show_file_list(update_obj, path):
    payload = {"path": path, "page": 1, "per_page": 0, "refresh": False}
    res = alist_api_call("/api/fs/list", data=payload)
    
    files = []
    if res and res.get('data'):
        files = res['data'].get('content', [])

    keyboard = []
    
    # Back button
    if path != "/":
        parent = os.path.dirname(path.rstrip("/"))
        if parent == "": parent = "/"
        keyboard.append([InlineKeyboardButton(".. (Back)", callback_data=f"nav|{parent}")])

    # Sort: Folders first
    files.sort(key=lambda x: x['is_dir'], reverse=True)

    # List items (Limit to 8 to avoid UI clutter)
    for f in files[:8]: 
        name = f['name']
        is_dir = f['is_dir']
        full_path = os.path.join(path, name)
        
        if is_dir:
            btn = InlineKeyboardButton(f"📁 {name}", callback_data=f"nav|{full_path}")
        else:
            btn = InlineKeyboardButton(f"🎬 {name}", callback_data=f"sel|{full_path}")
        keyboard.append([btn])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"📂 Path: {path}"
    if isinstance(update_obj, Update):
        await update_obj.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update_obj.edit_message_text(text, reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|", 1)
    action = data[0]
    payload = data[1]

    if action == "nav":
        await show_file_list(query, payload)
    
    elif action == "sel":
        keyboard = [
            [InlineKeyboardButton("▶️ Stream to Telegram", callback_data=f"run|{payload}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"nav|{os.path.dirname(payload)}")]
        ]
        await query.edit_message_text(f"File: {payload}\\nSelect Action:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "run":
        file_url = f"{ALIST_HOST}/d{payload}" 
        await query.edit_message_text(f"🚀 Triggering GitHub Action for:\\n{file_url}")
        trigger_github_workflow(file_url)

def trigger_github_workflow(file_url):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/stream.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_PAT}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "ref": "main",
        "inputs": {
            "file_url": file_url,
            "rtmp_server": RTMP_URL
        }
    }
    requests.post(url, json=data, headers=headers)

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ls', ls_command))
    application.add_handler(CommandHandler('download', download_command))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()
`;

// 3. GitHub Workflow
export const GITHUB_WORKFLOW_TEMPLATE = (config: StreamConfig) => `name: Stream to Telegram

on:
  workflow_dispatch:
    inputs:
      file_url:
        description: 'Direct Link to File'
        required: true
      rtmp_server:
        description: 'RTMP Server URL'
        required: true
        default: '${config.telegramRtmpUrl}'

jobs:
  stream:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Start Stream
        env:
          RTMP_URL: \${{ github.event.inputs.rtmp_server }}
          STREAM_KEY: \${{ secrets.TELEGRAM_STREAM_KEY }}
          FILE_URL: \${{ github.event.inputs.file_url }}
        run: |
          echo "Stream Source: $FILE_URL"
          ffmpeg -re -i "$FILE_URL" \\
            -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k \\
            -pix_fmt yuv420p -g 50 \\
            -c:a aac -b:a 128k -ac 2 -ar 44100 \\
            -f flv "$RTMP_URL$STREAM_KEY"
`;

export const SYSTEM_INSTRUCTION = `
You are a DevOps and Streaming expert specialized in Termux, Alist, GitHub Actions, and FFmpeg.
Guidelines:
1. Be concise.
2. If asked about Alist, explain how to add storage (Google Drive, PikPak, etc.).
3. If asked about FFmpeg, optimize parameters for Telegram.
`;
