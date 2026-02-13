import os
import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import ADMIN_ID, ALIST_HOST, ALIST_USER, ALIST_PASSWORD, RTMP_URL, logger
from modules import alist, tunnel, github, key_manager, updater, cache

# 使用单竖线作为分隔符 (Telegram Callback Data 限制 64 字节)
SEP = ":"

# --- 辅助函数 ---
def _get_icon(name, is_dir):
    if is_dir: return "📁"
    ext = os.path.splitext(name)[1].lower()
    if ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.ts', '.m3u8', '.wmv']: return "🎬"
    if ext in ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']: return "🎵"
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']: return "🖼️"
    if ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.iso']: return "📦"
    if ext in ['.py', '.sh', '.js', '.json', '.xml', '.html', '.txt', '.md']: return "📝"
    return "📄"

# --- 主菜单逻辑 ---

async def start(update: Update, context):
    """发送主菜单"""
    try:
        user_id = str(update.effective_user.id)
        if user_id != str(ADMIN_ID): 
            await update.message.reply_text(f"⛔️ 无权访问\nID: {user_id}")
            return
        
        context.user_data.clear()
        
        keyboard = [
            ["📂 浏览云盘", "🧲 离线下载"],
            ["🌐 远程访问", "🔐 登录信息"],
            ["🛑 停止推流", "🔑 密钥管理"],
            ["⚙️ 系统状态", "🔄 更新系统"]
        ]
        
        await update.message.reply_text(
            "👋 **StreamForge 控制台**\n(功能已完善)\n请选择操作：",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Start handler error: {e}", exc_info=True)
        await _reply_error(update, e)

async def download_command(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    context.user_data['state'] = 'AWAITING_LINK'
    await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**", parse_mode='Markdown')

async def menu_handler(update: Update, context):
    try:
        if str(update.effective_user.id) != str(ADMIN_ID): return
        msg = update.message.text.strip()
        
        # --- 状态机处理 (输入链接/密钥) ---
        state = context.user_data.get('state')
        
        if msg.startswith("magnet:?") or (msg.startswith("http") and not state):
            await handle_offline_download(update, msg)
            return

        if state == 'AWAITING_LINK':
            if msg == "/cancel":
                context.user_data.clear()
                await update.message.reply_text("已取消")
                return
            await handle_offline_download(update, msg)
            context.user_data['state'] = None
            return

        if state == 'AWAITING_KEY_NAME':
            context.user_data['new_key_name'] = msg
            context.user_data['state'] = 'AWAITING_KEY_VALUE'
            base_url = RTMP_URL if RTMP_URL else "⚠️ 未设置 (.env)"
            await update.message.reply_text(
                f"📝 名称: **{msg}**\n🔗 服务器: `{base_url}`\n\n👉 **请输入推流码 (Stream Key)**:",
                parse_mode='Markdown'
            )
            return
        
        if state == 'AWAITING_KEY_VALUE':
            name = context.user_data.get('new_key_name')
            try:
                keys = key_manager.load_keys()
                keys[name] = msg
                key_manager.save_keys(keys)
                await update.message.reply_text(f"✅ 密钥 **{name}** 已保存！")
            except Exception as e:
                await update.message.reply_text(f"❌ 保存失败: {e}")
            context.user_data['state'] = None
            return

        # --- 菜单按钮处理 ---
        
        if msg == "📂 浏览云盘":
            wait_msg = await update.message.reply_text("🔍 读取文件列表中...")
            await show_file_list(update, "/", 1, message_obj=wait_msg)
            
        elif msg == "🧲 离线下载":
            context.user_data['state'] = 'AWAITING_LINK'
            await update.message.reply_text("📥 **请发送链接** (Magnet/HTTP)", parse_mode='Markdown')

        elif msg == "🌐 远程访问":
            status_msg = await update.message.reply_text("⏳ 正在检查/操作 Cloudflare 隧道...")
            try:
                current_url = tunnel.get_tunnel_status()
                if current_url:
                    tunnel.stop_cloudflared()
                    await status_msg.edit_text("🚫 隧道已关闭。")
                else:
                    url, error_log = await tunnel.start_cloudflared()
                    if url:
                        await status_msg.edit_text(f"✅ **远程访问已开启**\n\n🔗 `{url}`", parse_mode='Markdown')
                    else:
                        await status_msg.edit_text(f"❌ **启动失败**\n日志:\n```\n{error_log}\n```", parse_mode='Markdown')
            except Exception as e:
                 await _reply_error(update, e)

        elif msg == "🔐 登录信息":
            url = tunnel.get_effective_public_url() or ALIST_HOST
            is_inner = "127.0.0.1" in url or "localhost" in url
            tag = "(仅内网)" if is_inner else "(公网)"
            await update.message.reply_text(
                f"🔐 **Alist 信息** {tag}\n🔗 `{url}`\n👤 `{ALIST_USER}`\n🔑 `{ALIST_PASSWORD}`",
                parse_mode='Markdown'
            )

        elif msg == "🔑 密钥管理":
            keys = key_manager.load_keys()
            text = "🔑 **推流密钥管理**\n点击删除或添加："
            keyboard = []
            for k, v in keys.items():
                keyboard.append([InlineKeyboardButton(f"🗑 删除: {k}", callback_data=f"del_key:{k}")])
            keyboard.append([InlineKeyboardButton("➕ 添加新密钥", callback_data="add_key")])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif msg == "🛑 停止推流":
            msg_obj = await update.message.reply_text("⏳ 正在连接 GitHub API...")
            success, res_text = github.stop_all_workflows()
            await msg_obj.edit_text(res_text)
            
        elif msg == "⚙️ 系统状态":
            alist_ok = alist.get_system_status()
            alist_str = "✅ 运行中" if alist_ok else "❌ 未响应"
            tunnel_url = tunnel.get_tunnel_status()
            tunnel_str = "✅ 开启" if tunnel_url else "⚪ 关闭"
            gh_status = "✅ 已配置" if github.GITHUB_PAT else "❌ 未配置"
            
            await update.message.reply_text(
                f"🖥 **系统状态诊断**\n\n"
                f"Alist 服务: {alist_str}\n"
                f"内网穿透: {tunnel_str}\n"
                f"GitHub Token: {gh_status}\n"
                f"Public URL: `{tunnel.get_effective_public_url()}`"
            , parse_mode='Markdown')

        elif msg == "🔄 更新系统":
            status_msg = await update.message.reply_text("⏳ 正在拉取代码更新...")
            should_restart, result_text = updater.update_repo()
            await status_msg.edit_text(result_text, parse_mode='Markdown')
            if should_restart:
                await asyncio.sleep(2)
                os._exit(0)

    except Exception as e:
        logger.error(f"Menu error: {e}", exc_info=True)
        await _reply_error(update, e)

async def handle_offline_download(update, url):
    msg = await update.message.reply_text("⏳ 提交中...")
    try:
        res = alist.add_aria2_task(url)
        if res.get('code') == 200:
            await msg.edit_text(f"✅ 任务已添加")
        else:
            await msg.edit_text(f"❌ 失败: {res.get('message')}")
    except Exception as e:
        await _reply_error(update, e)

async def show_file_list(update: Update, path, page, message_obj=None):
    if not message_obj:
        message_obj = update.callback_query.message if update.callback_query else update.message

    try:
        res = alist.get_file_list(path, page)
        
        if res.get('code') != 200:
            await message_obj.edit_text(
                f"❌ **Alist 读取失败**\n"
                f"Code: `{res.get('code')}`\n"
                f"Msg: `{res.get('message')}`\n\n"
                f"建议检查 Alist 服务状态或发送 '🔄 更新系统'。"
            , parse_mode='Markdown')
            return

        content = res.get('data', {}).get('content', [])
        total = res.get('data', {}).get('total', 0)
        
        if content is None: content = []
        # 排序：文件夹在前，然后按名称排序（忽略大小写）
        content.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        buttons = []
        
        # 缓存当前路径用于刷新
        current_path_id = cache.cache_path(path)
        
        # --- 导航栏 ---
        nav_top = []
        if path != "/":
            parent = os.path.dirname(path.rstrip('/'))
            if not parent: parent = "/"
            parent_id = cache.cache_path(parent)
            nav_top.append(InlineKeyboardButton("🔙 上级", callback_data=f"nav:{parent_id}:1"))
        
        nav_top.append(InlineKeyboardButton("🔄 刷新", callback_data=f"nav:{current_path_id}:{page}"))
        
        if path != "/":
            root_id = cache.cache_path("/")
            nav_top.append(InlineKeyboardButton("🏠 首页", callback_data=f"nav:{root_id}:1"))
            
        if nav_top: buttons.append(nav_top)

        # --- 文件列表 ---
        for item in content:
            name = item['name']
            is_dir = item['is_dir']
            icon = _get_icon(name, is_dir)
            
            display_name = (name[:20] + '..') if len(name) > 20 else name
            
            # 拼接完整路径
            if path == "/": full_path = f"/{name}"
            else: full_path = f"{path.rstrip('/')}/{name}"
            
            # 缓存路径，获取短ID
            path_id = cache.cache_path(full_path)
            
            if is_dir:
                # nav:UUID:1
                buttons.append([InlineKeyboardButton(f"{icon} {display_name}", callback_data=f"nav:{path_id}:1")])
            else:
                # pre:UUID
                buttons.append([InlineKeyboardButton(f"{icon} {display_name}", callback_data=f"pre:{path_id}")])

        # --- 翻页 ---
        nav_row = []
        if page > 1: 
            nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"nav:{current_path_id}:{page-1}"))
        if page * 10 < total: 
            nav_row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"nav:{current_path_id}:{page+1}"))
        if nav_row: buttons.append(nav_row)

        markup = InlineKeyboardMarkup(buttons)
        text = f"📂 **当前目录**: `{path}`\n📄 页码: {page} / 项目数: {total}"
        
        if hasattr(message_obj, 'edit_text'):
             await message_obj.edit_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
             await message_obj.reply_text(text, reply_markup=markup, parse_mode='Markdown')
             
    except Exception as e:
        logger.error(f"List error: {e}", exc_info=True)
        await _reply_error(update, e)

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data.split(SEP)
        action = data[0]

        if action == "nav": # nav:UUID:PAGE
            path_id = data[1]
            page = int(data[2])
            path = cache.get_path(path_id)
            
            if not path:
                # 缓存失效，回首页
                await show_file_list(update, "/", 1)
                return
            
            await show_file_list(update, path, page)
        
        elif action == "pre": # pre:UUID
            path_id = data[1]
            path = cache.get_path(path_id)
            
            if not path:
                await query.message.edit_text("⚠️ 路径缓存已失效，请重新点击 '浏览云盘'。")
                return

            context.user_data['pending_path'] = path
            keys = key_manager.load_keys()
            
            btns = []
            if not keys:
                btns.append([InlineKeyboardButton("➕ 无密钥，点击添加", callback_data="add_key_shortcut")])
            else:
                for k in keys:
                    btns.append([InlineKeyboardButton(f"📡 推流到: {k}", callback_data=f"stream:{k}")])
            
            # 返回按钮
            parent = os.path.dirname(path.rstrip('/'))
            if not parent: parent = "/"
            parent_id = cache.cache_path(parent)
            
            btns.append([InlineKeyboardButton("🔙 返回目录", callback_data=f"nav:{parent_id}:1")])
            
            await query.message.edit_text(
                f"🎬 **准备推流**\n\n📄 文件: `{os.path.basename(path)}`\n📂 路径: `{path}`\n\n👇 请选择推流目标:", 
                reply_markup=InlineKeyboardMarkup(btns), 
                parse_mode='Markdown'
            )

        elif action == "stream": # stream:KEY_NAME
            key_name = data[1]
            path = context.user_data.get('pending_path')
            
            if not path:
                await query.message.edit_text("❌ 操作已过期。")
                return

            key_val = key_manager.load_keys().get(key_name)
            if not RTMP_URL:
                 await query.message.edit_text(f"❌ `.env` 未配置 `RTMP_URL`")
                 return
            
            final_target = f"{RTMP_URL}{key_val}"
            
            await query.message.edit_text(f"🔄 **正在处理**\n1. 获取文件直链...", parse_mode='Markdown')
            
            # 获取链接
            raw_url, err_msg = alist.get_file_url(path)
            if not raw_url:
                await query.message.edit_text(f"❌ 获取链接失败:\n`{err_msg}`", parse_mode='Markdown')
                return

            await query.message.edit_text(f"🔄 **正在处理**\n2. 触发 GitHub Actions...\n🔗 `{raw_url[:40]}...`", parse_mode='Markdown')
            
            success, msg = github.trigger_github_workflow(raw_url, final_target)
            
            if success:
                await query.message.edit_text(f"✅ **推流已启动！**\n\n📡 目标: `{key_name}`\n📄 反馈: {msg}")
            else:
                await query.message.edit_text(f"❌ **请求失败**\n\n{msg}")

        elif action == "add_key":
            context.user_data['state'] = 'AWAITING_KEY_NAME'
            await query.message.reply_text("⌨️ 请输入新配置的 **名称** (如: Live1):")
            
        elif action == "add_key_shortcut":
            context.user_data['state'] = 'AWAITING_KEY_NAME'
            await query.message.reply_text("⌨️ 请输入新配置的 **名称**:")
            
        elif action == "del_key":
            key = data[1]
            keys = key_manager.load_keys()
            if key in keys:
                del keys[key]
                key_manager.save_keys(keys)
                # 刷新列表
                keyboard = []
                for k, v in keys.items():
                    keyboard.append([InlineKeyboardButton(f"🗑 删除: {k}", callback_data=f"del_key:{k}")])
                keyboard.append([InlineKeyboardButton("➕ 添加新密钥", callback_data="add_key")])
                await query.message.edit_text("🔑 **推流密钥管理**\n已删除，请继续操作：", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "cancel":
            await query.message.delete()
            
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await _reply_error(update, e)

async def _reply_error(update, e):
    try:
        tb = traceback.format_exc()[-1000:]
        text = f"❌ **执行错误**\n`{str(e)}`\n\n日志:\n```\n{tb}\n```"
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, parse_mode='Markdown')
    except: pass
