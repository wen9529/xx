#!/bin/bash
# StreamForge Ultimate Setup Script

echo "🚀 Starting Setup..."
pkg update -y
pkg install -y python alist aria2 nodejs git ffmpeg
npm install -g pm2
pip install python-telegram-bot requests python-dotenv

# Generate Aria2 Secret if empty
ARIA_RPC="streamforge"

echo "⚙️  Configuring Environment..."
# Ensure the user has provided inputs via environment variables or interactive prompt in real usage.
# For this script generation, we rely on the React app injecting values via .env or manual edit.
# Here we just ensure the file structure is correct.

# This block assumes the script is generated with values filled in.
# If running raw, users should edit .env manually.

echo "📥 Configuring Aria2 for Alist..."
mkdir -p ~/.config/aria2
cat << EOF > ~/.config/aria2/aria2.conf
enable-rpc=true
rpc-allow-origin-all=true
rpc-listen-all=true
rpc-secret=$ARIA_RPC
EOF

# Ensure bot.py exists (the React app generates this content usually)
if [ ! -f bot.py ]; then
    echo "⚠️  bot.py not found. Please ensure you copy the bot code."
    touch bot.py
fi

echo "✅ Starting Services..."
# Start Aria2 in background
pm2 start aria2c --name aria2 -- --conf-path=$HOME/.config/aria2/aria2.conf -D
# Start Alist
pm2 start alist --name alist -- server
# Start Bot
pm2 start bot.py --name stream-bot --interpreter python

pm2 save
echo "🎉 Done! Services started."
echo "Alist URL: http://127.0.0.1:5244"
echo "Alist Admin Password: Check logs 'pm2 logs alist'"
