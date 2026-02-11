import { StreamConfig } from "./types";

export const DEFAULT_STREAM_CONFIG: StreamConfig = {
  githubUser: "your-username",
  githubRepo: "stream-repo",
  githubPat: "",
  telegramBotToken: "",
  telegramAdminId: "",
  telegramRtmpUrl: "rtmp://x.rtmp.t.me/s/",
  telegramStreamKey: "",
  alistPassword: "admin", // Default password
  fileName: "movie.mp4",
  fileUrl: "",
};

// .env File Template (For display and reference)
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

# StreamForge - Termux Deployment Script
# Installs Alist, Python, configures environment, and sets Alist password.

echo "🚀 Starting StreamForge Deployment..."

# 1. Update Termux & Install Dependencies
echo "📦 Installing dependencies..."
pkg update -y && pkg upgrade -y
pkg install alist python git -y

# 2. Setup Python Environment
echo "🐍 Setting up Python dependencies..."
pip install python-telegram-bot requests python-dotenv

# 3. Create .env file
# IMPORTANT: This file contains secrets. If your repo is public, do NOT include this script with secrets hardcoded.
echo "🔐 Configuring secrets..."
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

# 4. Start Alist and Set Password
echo "📂 Starting Alist Server..."
if pgrep -x "alist" > /dev/null; then
    echo "Alist is already running."
else
    alist server > alist.log 2>&1 &
    echo "Waiting for Alist to initialize..."
    sleep 5
fi

# Set the Alist password automatically
echo "🔑 Setting Alist admin password..."
./alist admin set ${config.alistPassword}

# 5. Start the Telegram Bot
echo "🤖 Starting StreamForge Bot..."
echo "✅ Deployment Complete! Send /start to your bot."
python bot.py
`;

// 2. Python Telegram Bot Script (Enhanced with Alist Browsing)
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

logging.basicConfig(level=logging.INFO)
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

def list_alist_files(path="/"):
    global alist_token
    if not alist_token:
        get_alist_token()
    
    url = f"{ALIST_HOST}/api/fs/list"
    headers = {"Authorization": alist_token}
    data = {"path": path, "page": 1, "per_page": 0, "refresh": False}
    
    try:
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 200:
            return res.json().get('data', {}).get('content', [])
    except Exception as e:
        logger.error(f"List Files Error: {e}")
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "👋 StreamForge Bot Ready!\\n"
        "Commands:\\n"
        "/ls - Browse Alist Files\\n"
        "Or send a direct link to stream."
    )

async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await show_file_list(update, "/")

async def show_file_list(update_obj, path):
    files = list_alist_files(path)
    keyboard = []
    
    # Back button
    if path != "/":
        parent = os.path.dirname(path.rstrip("/"))
        if parent == "": parent = "/"
        keyboard.append([InlineKeyboardButton(".. (Back)", callback_data=f"nav|{parent}")])

    # List items (Limit to 10 to avoid limit)
    for f in files[:10]: 
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
        # It's a callback query
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
        # Ask for confirmation
        keyboard = [
            [InlineKeyboardButton("▶️ Start Streaming", callback_data=f"run|{payload}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"nav|{os.path.dirname(payload)}")]
        ]
        await query.edit_message_text(f"Selected: {payload}\\nReady to stream?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "run":
        # Construct Direct Link (Assumes Alist allows public guest access or we sign it)
        # For simplicity, we assume guest access is on or we use the raw link structure
        # A robust way requires getting the download url via API
        file_url = f"{ALIST_HOST}/d{payload}" # Typical Alist Direct Link pattern /d/path
        
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
