#!/bin/bash
# StreamForge Ultimate Setup Script

echo "🚀 Starting Setup..."

# 0. Create .env config file FIRST (Ensures variables are saved even if install fails)
echo "⚙️  Configuring Environment Variables..."
cat << EOF > .env
${GENERATE_ENV_CONTENT(config)}
EOF

# 1. Update and Install System Packages
echo "📦 Installing System Packages..."
pkg update -y
pkg install -y python alist aria2 nodejs git ffmpeg

# 2. Install Node.js Global Packages
echo "📦 Installing PM2..."
npm install -g pm2

# 3. Install Python Dependencies
echo "📦 Installing Python Libs..."
pip install python-telegram-bot requests python-dotenv

# Generate Aria2 Secret if empty
ARIA_RPC=${config.aria2Secret}

echo "📥 Configuring Aria2 for Alist..."
mkdir -p ~/.config/aria2
cat << EOF > ~/.config/aria2/aria2.conf
enable-rpc=true
rpc-allow-origin-all=true
rpc-listen-all=true
rpc-secret=$ARIA_RPC
EOF

echo "📄 Creating Intelligent Bot..."
cat << 'PYTHON_EOF' > bot.py
${PYTHON_BOT_SCRIPT}
PYTHON_EOF

echo "✅ Starting Services..."
# Start Aria2 in background
pm2 start aria2c --name aria2 -- --conf-path=$HOME/.config/aria2/aria2.conf -D
# Start Alist
pm2 start alist --name alist -- server
# Start Bot
pm2 start bot.py --name stream-bot --interpreter python

pm2 save
echo "🎉 Done! Alist Aria2 Secret: $ARIA_RPC"
echo "ℹ️  Bot Token & Config saved to .env file"
