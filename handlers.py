import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import ADMIN_ID, ALIST_HOST, ALIST_USER, ALIST_PASSWORD, RTMP_URL
from modules import alist, tunnel, github, key_manager

async def start(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): 
        await update.message.reply_text("⛔️ 无权访问")
        return
    
    context.user_data.clear()
    
    keyboard = [
        ["📂 浏览云盘"],
        ["🧲 离线下载 (Magnet/HTTP)"],
        ["🌐 开启/关闭 远程访问", "🔐 查看登录信息"],
        ["🛑 停止推流", "🔑 密钥管理"],
        ["⚙️ 系统状态"]
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
    if str(update.effective_user.id) != str(ADMIN_ID): return
    context.user_data['state'] = 'AWAITING_LINK'
    await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**", parse_mode='Markdown')

async def menu_handler(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    msg = update.message.text.strip()
    
    # 1. 快速下载
    if msg.startswith("magnet:?") or (msg.startswith("http") and not context.user_data.get('state')):
        await handle_offline_download(update, msg)
        return

    # 2. 状态机处理
    state = context.user_data.get('state')
    if state == 'AWAITING_LINK':
        if msg == "/cancel":
            context.user_data.clear()
            await update.message.reply_text("已取消")
            await start(update, context)
            return
        await handle_offline_download(update, msg)
        context.user_data['state'] = None
        return

    if state == 'AWAITING_KEY_NAME':
        context.user_data['new_key_name'] = msg
        context.user_data['state'] = 'AWAITING_KEY_URL'
        await update.message.reply_text(f"📝 名称: {msg}\n👉 请输入完整 RTMP 地址:")
        return
    
    if state == 'AWAITING_KEY_URL':
        name = context.user_data.get('new_key_name')
        keys = key_manager.load_keys()
        keys[name] = msg
        key_manager.save_keys(keys)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ 密钥 **{name}** 已保存", parse_mode='Markdown')
        return

    # 3. 菜单按钮
    if msg == "📂 浏览云盘":
        await update.message.reply_text("🔍 读取根目录...")
        await show_file_list(update, "/", 1)
        
    elif msg == "🧲 离线下载 (Magnet/HTTP)":
        context.user_data['state'] = 'AWAITING_LINK'
        await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**\n(或者直接粘贴链接给我，无需点此按钮)", parse_mode='Markdown')

    elif msg == "🌐 开启/关闭 远程访问":
        current_url = tunnel.get_tunnel_status()
        if current_url:
            tunnel.stop_cloudflared()
            await update.message.reply_text("🚫 隧道已关闭。外网访问已停止。")
        else:
            msg_wait = await update.message.reply_text("⏳ 正在启动 Cloudflare 隧道 (需 5-10 秒)...")
            url = await tunnel.start_cloudflared()
            if url:
                await msg_wait.edit_text(f"✅ **远程访问已开启**\n\n🔗 公网地址: `{url}`\n\n您现在可以在外网访问 Alist 管理页面。", parse_mode='Markdown')
            else:
                await msg_wait.edit_text("❌ 启动失败。请确保已安装 cloudflared。")

    elif msg == "🔐 查看登录信息":
        url = tunnel.get_effective_public_url() or ALIST_HOST
        status = " (内网)" if "127.0.0.1" in url else " (公网)"
        await update.message.reply_text(
            f"🔐 **Alist 登录凭证**{status}\n\n🔗 地址: `{url}`\n👤 用户: `{ALIST_USER}`\n🔑 密码: `{ALIST_PASSWORD}`",
            parse_mode='Markdown'
        )

    elif msg == "🔑 密钥管理":
        keys = key_manager.load_keys()
        text = "🔑 **保存的推流地址**：\n"
        keyboard = []
        for k, v in keys.items():
            text += f"- {k}\n"
            keyboard.append([InlineKeyboardButton(f"🗑 删除 {k}", callback_data=f"delkey|{k}")])
        keyboard.append([InlineKeyboardButton("➕ 添加新地址", callback_data="addkey")])
        await update.message.reply_text(text or "暂无保存的地址", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif msg == "🛑 停止推流":
        msg_obj = await update.message.reply_text("🛑 正在停止 GitHub 任务...")
        success, res_text = github.stop_all_workflows()
        await msg_obj.edit_text(res_text)
        
    elif msg == "⚙️ 系统状态":
        alist_ok = alist.get_system_status()
        alist_str = "✅ Alist 运行中" if alist_ok else "❌ Alist 未响应"
        tunnel_url = tunnel.get_tunnel_status()
        tunnel_str = f"✅ 隧道开启 ({tunnel_url})" if tunnel_url else "⚪ 隧道关闭"
        
        await update.message.reply_text(f"🖥 **系统状态**:\n{alist_str}\n{tunnel_str}", parse_mode='Markdown')

async def handle_offline_download(update, url):
    await update.message.reply_text("⏳ 正在提交 Aria2 离线任务...")
    res = alist.add_aria2_task(url)
    if res.get('code') == 200:
        await update.message.reply_text(f"✅ 任务已添加！\n文件将下载到根目录。")
    else:
        await update.message.reply_text(f"❌ 添加失败: {res.get('message')}")

async def show_file_list(update: Update, path, page):
    is_cb = bool(update.callback_query)
    message = update.callback_query.message if is_cb else update.message
    
    res = alist.get_file_list(path, page)
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
        keys = key_manager.load_keys()
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

        target_rtmp = RTMP_URL if key_name == "default" else key_manager.load_keys().get(key_name)
        if not target_rtmp:
            await query.message.edit_text("❌ 无效的推流地址")
            return

        await query.message.edit_text(f"🔄 正在获取直链...\n文件: `{os.path.basename(path)}`", parse_mode='Markdown')
        
        raw_url, err_msg = alist.get_file_url(path)
        
        if not raw_url:
            await query.message.edit_text(f"❌ 无法获取文件直链: {err_msg}")
            return

        success, msg = github.trigger_github_workflow(raw_url, target_rtmp)
        icon = "✅" if success else "❌"
        await query.message.reply_text(f"{icon} 推流请求结果: {msg}")

    elif action == "addkey":
        context.user_data['state'] = 'AWAITING_KEY_NAME'
        await query.message.reply_text("⌨️ 请输入新推流地址的名称 (例如: Live1):")
        
    elif action == "delkey":
        keys = key_manager.load_keys()
        if data[1] in keys:
            del keys[data[1]]
            key_manager.save_keys(keys)
            await query.message.reply_text(f"🗑 已删除 {data[1]}")
    
    elif action == "cancel":
        await query.message.delete()
