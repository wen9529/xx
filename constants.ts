import { StreamConfig } from "./types";

export const DEFAULT_STREAM_CONFIG: StreamConfig = {
  githubUser: "your-username",
  githubRepo: "stream-repo",
  githubPat: "",
  telegramBotToken: "",
  telegramAdminId: "",
  telegramRtmpUrl: "rtmp://x.rtmp.t.me/s/",
  telegramStreamKey: "",
  fileName: "movie.mp4",
  fileUrl: "",
};

// 1. Termux One-Click Setup Script
export const TERMUX_SETUP_SCRIPT = (config: StreamConfig) => `#!/bin/bash

# StreamForge - Termux Deployment Script
# This script installs Alist, Python environment, and starts the management bot.

echo "🚀 Starting StreamForge Deployment..."

# 1. Update Termux & Install Dependencies
echo "📦 Installing dependencies..."
pkg update -y && pkg upgrade -y
pkg install alist python git -y

# 2. Setup Python Environment for the Bot
echo "🐍 Setting up Python dependencies..."
pip install python-telegram-bot requests

# 3. Create .env file for the Bot (Security best practice)
echo "🔐 Configuring secrets..."
cat << EOF > .env
TG_BOT_TOKEN=${config.telegramBotToken}
TG_ADMIN_ID=${config.telegramAdminId}
GITHUB_OWNER=${config.githubUser}
GITHUB_REPO=${config.githubRepo}
GITHUB_PAT=${config.githubPat}
RTMP_URL=${config.telegramRtmpUrl}
EOF

# 4. Start Alist in background
echo "📂 Starting Alist Server..."
if pgrep -x "alist" > /dev/null
then
    echo "Alist is already running."
else
    alist server > alist.log 2>&1 &
    echo "Alist started. Default password info:"
    alist admin
fi

# 5. Start the Telegram Bot
echo "🤖 Starting Telegram Control Bot..."
echo "✅ Deployment Complete! Check your Telegram Bot."
python bot.py
`;

// 2. Python Telegram Bot Script
export const PYTHON_BOT_SCRIPT = `import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = int(os.getenv("TG_ADMIN_ID"))
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_PAT = os.getenv("GITHUB_PAT")
RTMP_URL = os.getenv("RTMP_URL")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("👋 StreamForge Bot Ready!\\nSend me a direct file link to stream it.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    if text.startswith("http"):
        # Assume it's a link to stream
        keyboard = [
            [InlineKeyboardButton("🚀 Stream to Telegram", callback_data=f"stream|{text}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"File detected: {text}\\nSelect action:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please send a valid HTTP link.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    action = data[0]
    link = data[1]

    if action == "stream":
        await query.edit_message_text(text=f"⏳ Triggering GitHub Workflow for:\\n{link}")
        trigger_github_workflow(link, query)

def trigger_github_workflow(file_url, query):
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
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 204:
        # We can't await in a sync function call easily without extra setup, 
        # but in a real deployment this would be async or handled better.
        print("Workflow triggered successfully")
    else:
        print(f"Failed to trigger workflow: {response.text}")

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: TG_BOT_TOKEN not found.")
        exit(1)
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button))
    
    print("Bot is polling...")
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
          echo "Starting stream source: $FILE_URL"
          ffmpeg -re -i "$FILE_URL" \\
            -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k \\
            -pix_fmt yuv420p -g 50 \\
            -c:a aac -b:a 128k -ac 2 -ar 44100 \\
            -f flv "$RTMP_URL$STREAM_KEY"
`;

export const SYSTEM_INSTRUCTION = `
You are a DevOps and Streaming expert specialized in Termux, Alist, GitHub Actions, and FFmpeg.
Your goal is to help the user set up a pipeline where they host files on Alist (running on Termux or elsewhere), 
and use GitHub Actions to pull that file and stream it to Telegram via RTMP.

Guidelines:
1. Be concise and technical.
2. If asked about Alist, explain how to add storage (Google Drive, PikPak, etc.).
3. If asked about FFmpeg, optimize parameters for Telegram (usually 3000k bitrate, 30fps, AAC audio).
4. If asked about GitHub Actions, ensure secrets usage is emphasized for Stream Keys.
5. Provide specific commands.
`;
