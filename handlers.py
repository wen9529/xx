import os
import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import ADMIN_ID, ALIST_HOST, ALIST_USER, ALIST_PASSWORD, RTMP_URL, logger
from modules import alist, tunnel, github, key_manager, updater

# 使用单竖线作为分隔符
SEP = "|"

async def start(update: Update, context):
    """发送主菜单"""
    try:
        user_id = str(update.effective_user.id)
        admin_id = str(ADMIN_ID)
        
        logger.info(f"User {user_id} triggered /start")
        
        if user_id != admin_id: 
            logger.warning(f"Unauthorized access attempt by {user_id}")
            await update.message.reply_text(f"⛔️ 无权访问\nID: {user_id}")
            return
        
        context.user_data.clear()
        
        keyboard = [
            ["📂 浏览云盘"],
            ["🧲 离线下载"],
            ["🌐 远程访问", "🔐 登录信息"],
            ["🛑 停止推流", "🔑 密钥管理"],
            ["⚙️ 系统状态", "🔄 更新系统"]
        ]
        
        await update.message.reply_text(
            "👋 **StreamForge 控制台**\n请选择操作：",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Start handler error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 初始化失败: {e}")

async def download_command(update: Update, context):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    context.user_data['state'] = 'AWAITING_LINK'
    await update.message.reply_text("📥 **请发送磁力链接 (Magnet) 或 HTTP 链接**", parse_mode='Markdown')

async def menu_handler(update: Update, context):
    """处理主菜单点击"""
    try:
        if str(update.effective_user.id) != str(ADMIN_ID): return
        msg = update.message.text.strip()
        logger.info(f"Menu action: {msg}")
        
        # 1. 优先处理状态机
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
            base_url = RTMP_URL if RTMP_URL else "未设置(请检查.env)"
            await update.message.reply_text(
                f"📝 名称: **{msg}**\n"
                f"🔗 固定服务器: `{base_url}`\n\n"
                f"👉 **请输入推流码 (Stream Key)**:\n"
                f"(例如: `user_123?token=abc`，它将拼接到服务器地址后)",
                parse_mode='Markdown'
            )
            return
        
        if state == 'AWAITING_KEY_VALUE':
            name = context.user_data.get('new_key_name')
            try:
                keys = key_manager.load_keys()
                keys[name] = msg
                key_manager.save_keys(keys)
                logger.info(f"New key saved: {name}")
                await update.message.reply_text(f"✅ 密钥 **{name}** 已保存！", parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Save key error: {e}")
                await update.message.reply_text(f"❌ 保存密钥失败: {e}")
            context.user_data['state'] = None
            return

        # 2. 菜单按钮响应
        if msg == "📂 浏览云盘":
            wait_msg = await update.message.reply_text("🔍 正在请求 Alist 接口...")
            await show_file_list(update, "/", 1, message_obj=wait_msg)
            
        elif msg == "🧲 离线下载":
            context.user_data['state'] = 'AWAITING_LINK'
            await update.message.reply_text("📥 **请发送链接** (Magnet/HTTP)", parse_mode='Markdown')

        elif msg == "🌐 远程访问":
            status_msg = await update.message.reply_text("⏳ 正在操作 Cloudflare 隧道 (可能需要 10-20 秒)...")
            try:
                current_url = tunnel.get_tunnel_status()
                if current_url:
                    tunnel.stop_cloudflared()
                    logger.info("Tunnel stopped by user")
                    await status_msg.edit_text("🚫 隧道已关闭。")
                else:
                    url = await tunnel.start_cloudflared()
                    if url:
                        logger.info(f"Tunnel started: {url}")
                        await status_msg.edit_text(f"✅ **远程访问已开启**\n\n🔗 地址: `{url}`", parse_mode='Markdown')
                    else:
                        logger.error("Tunnel start failed")
                        await status_msg.edit_text("❌ 启动失败。请检查后台日志 `tunnel.log`。\n可能原因: 网络问题或 cloudflared 未安装。")
            except Exception as e:
                 logger.error(f"Tunnel toggle error: {e}", exc_info=True)
                 await status_msg.edit_text(f"❌ 隧道操作异常: {e}")

        elif msg == "🔐 登录信息":
            url = tunnel.get_effective_public_url() or ALIST_HOST
            is_public = "trycloudflare" in url
            tag = "(公网)" if is_public else "(内网)"
            await update.message.reply_text(
                f"🔐 **Alist 凭证** {tag}\n\n"
                f"🔗 `{url}`\n"
                f"👤 `{ALIST_USER}`\n"
                f"🔑 `{ALIST_PASSWORD}`",
                parse_mode='Markdown'
            )

        elif msg == "🔑 密钥管理":
            keys = key_manager.load_keys()
            base_url = RTMP_URL if RTMP_URL else "⚠️ 未设置 RTMP_URL (.env)"
            text = f"🔑 **推流配置**\n📍 固定服务器: `{base_url}`\n\n👇 **已保存的密钥 (后缀)**:"
            
            keyboard = []
            for k, v in keys.items():
                display_v = v[:10] + "..." if len(v) > 10 else v
                text += f"\n- **{k}**: `{display_v}`"
                keyboard.append([InlineKeyboardButton(f"🗑 删除 {k}", callback_data=f"delkey{SEP}{k}")])
            
            keyboard.append([InlineKeyboardButton("➕ 添加新密钥", callback_data="addkey")])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        elif msg == "🛑 停止推流":
            msg_obj = await update.message.reply_text("⏳ 正在请求 GitHub API 停止任务...")
            success, res_text = github.stop_all_workflows()
            await msg_obj.edit_text(res_text)
            
        elif msg == "⚙️ 系统状态":
            alist_ok = alist.get_system_status()
            alist_str = "✅ 运行中" if alist_ok else "❌ 未响应 (请检查 PM2 日志)"
            tunnel_url = tunnel.get_tunnel_status()
            tunnel_str = "✅ 开启" if tunnel_url else "⚪ 关闭"
            await update.message.reply_text(f"🖥 **系统状态**\nAlist: {alist_str}\n隧道: {tunnel_str}")

        elif msg == "🔄 更新系统":
            status_msg = await update.message.reply_text("⏳ 正在拉取代码更新...")
            should_restart, result_text = updater.update_repo()
            await status_msg.edit_text(result_text, parse_mode='Markdown')
            if should_restart:
                await asyncio.sleep(2)
                os._exit(0)
                
    except Exception as e:
        logger.error(f"Menu error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ **操作发生错误**: \n`{str(e)}`", parse_mode='Markdown')

async def handle_offline_download(update, url):
    msg = await update.message.reply_text("⏳ 提交 Aria2 任务中...")
    try:
        res = alist.add_aria2_task(url)
        if res.get('code') == 200:
            logger.info(f"Download task added: {url}")
            await msg.edit_text(f"✅ 下载任务已添加！")
        else:
            logger.error(f"Download task failed: {res}")
            await msg.edit_text(f"❌ 添加失败: {res.get('message')}\n请确保 Alist 后台 Aria2 配置正确。")
    except Exception as e:
        logger.error(f"Download exception: {e}")
        await msg.edit_text(f"❌ 异常: {e}")

async def show_file_list(update: Update, path, page, message_obj=None):
    """显示文件列表，优化了路径处理和错误捕获"""
    if not message_obj:
        message_obj = update.callback_query.message if update.callback_query else update.message

    try:
        res = alist.get_file_list(path, page)
        if res.get('code') != 200:
            error_msg = res.get('message', '未知错误')
            logger.error(f"List files failed: {error_msg}")
            text = f"❌ **无法读取目录**\n\n原因: `{error_msg}`\n\n请检查 Alist 是否运行中。"
            if hasattr(message_obj, 'edit_text'): await message_obj.edit_text(text, parse_mode='Markdown')
            else: await message_obj.reply_text(text, parse_mode='Markdown')
            return

        content = res['data']['content'] or []
        total = res['data']['total']
        content.sort(key=lambda x: x['is_dir'], reverse=True)
        
        buttons = []
        # 返回上级
        if path != "/":
            parent = os.path.dirname(path.rstrip('/'))
            if not parent: parent = "/"
            buttons.append([InlineKeyboardButton("🔙 返回上级", callback_data=f"n{SEP}{parent}{SEP}1")])
        
        for item in content:
            name = item['name']
            display_name = (name[:15] + '..') if len(name) > 15 else name
            
            # 路径拼接
            if path == "/":
                full_path = f"/{name}"
            else:
                full_path = f"{path.rstrip('/')}/{name}"
                
            cb_data = ""
            if item['is_dir']:
                cb_data = f"n{SEP}{full_path}{SEP}1"
                if len(cb_data.encode('utf-8')) >= 64:
                    buttons.append([InlineKeyboardButton(f"📁 {display_name} (路径过长)", callback_data="noop")])
                else:
                    buttons.append([InlineKeyboardButton(f"📁 {display_name}", callback_data=cb_data)])
            else:
                cb_data = f"p{SEP}{full_path}"
                if len(cb_data.encode('utf-8')) >= 64:
                     buttons.append([InlineKeyboardButton(f"▶️ {display_name} (文件名过长)", callback_data="noop")])
                else:
                     buttons.append([InlineKeyboardButton(f"▶️ {display_name}", callback_data=cb_data)])

        # 翻页
        nav_row = []
        if page > 1: nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"n{SEP}{path}{SEP}{page-1}"))
        if page * 10 < total: nav_row.append(InlineKeyboardButton("➡️", callback_data=f"n{SEP}{path}{SEP}{page+1}"))
        if nav_row: buttons.append(nav_row)

        markup = InlineKeyboardMarkup(buttons)
        text = f"📂 **目录**: `{path}`"
        
        if hasattr(message_obj, 'edit_text'):
             await message_obj.edit_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
             await message_obj.reply_text(text, reply_markup=markup, parse_mode='Markdown')
             
    except Exception as e:
        logger.error(f"Show file list exception: {e}", exc_info=True)
        if hasattr(message_obj, 'edit_text'):
            await message_obj.edit_text(f"❌ 读取列表发生异常: {e}")
        else:
            await message_obj.reply_text(f"❌ 读取列表发生异常: {e}")

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data.split(SEP)
        action = data[0]

        logger.info(f"Callback Action: {action}, Data: {query.data}")

        if action == "noop":
            await query.message.reply_text("⚠️ 此项目路径或名称过长，Telegram 按钮限制无法操作，请尝试重命名文件。")
            return

        if action == "n": # nav
            page = int(data[-1])
            path = SEP.join(data[1:-1])
            await show_file_list(update, path, int(page))
        
        elif action == "p": # pre_stream
            path = SEP.join(data[1:])
            context.user_data['pending_path'] = path
            keys = key_manager.load_keys()
            
            btns = []
            if not keys:
                btns.append([InlineKeyboardButton("⚠️ 无密钥 (请去密钥管理添加)", callback_data="cancel")])
            else:
                for k in keys:
                    btns.append([InlineKeyboardButton(f"📡 推流到: {k}", callback_data=f"s{SEP}{k}")])
            
            btns.append([InlineKeyboardButton("❌ 取消", callback_data="cancel")])
            
            await query.message.edit_text(
                f"🎬 **准备推流**\n文件: `{os.path.basename(path)}`\n\n请选择推流配置:", 
                reply_markup=InlineKeyboardMarkup(btns), 
                parse_mode='Markdown'
            )

        elif action == "s": # stream
            key_name = data[1]
            path = context.user_data.get('pending_path')
            
            if not path:
                await query.message.edit_text("❌ 操作已过期，请重新浏览文件。")
                return

            key_val = key_manager.load_keys().get(key_name)
            
            if not RTMP_URL:
                 await query.message.edit_text(f"❌ 错误: `.env` 中未配置 `RTMP_URL`。")
                 return
                 
            final_target = f"{RTMP_URL}{key_val}"
            
            logger.info(f"Initiating stream for {path} to {key_name}")

            await query.message.edit_text(f"🔄 获取文件直链中...\n📄 `{os.path.basename(path)}`", parse_mode='Markdown')
            
            raw_url, err_msg = alist.get_file_url(path)
            if not raw_url:
                logger.error(f"Get file url failed: {err_msg}")
                await query.message.edit_text(f"❌ 获取直链失败: {err_msg}")
                return

            await query.message.edit_text(f"🚀 正在触发 GitHub Actions...\n目标: `{key_name}`", parse_mode='Markdown')
            
            success, msg = github.trigger_github_workflow(raw_url, final_target)
            
            if success:
                logger.info("GitHub workflow triggered successfully")
                await query.message.edit_text(f"✅ **推流已开始！**\n\nGitHub 反馈: {msg}")
            else:
                logger.error(f"GitHub workflow failed: {msg}")
                await query.message.edit_text(f"❌ **推流请求失败**\n\n错误日志: `{msg}`", parse_mode='Markdown')

        elif action == "addkey":
            context.user_data['state'] = 'AWAITING_KEY_NAME'
            await query.message.reply_text("⌨️ 请输入新配置的 **名称** (例如: `Live1`):")
            
        elif action == "delkey":
            key_to_del = data[1]
            keys = key_manager.load_keys()
            if key_to_del in keys:
                del keys[key_to_del]
                key_manager.save_keys(keys)
                logger.info(f"Deleted key: {key_to_del}")
                await query.message.reply_text(f"🗑 已删除 {key_to_del}")
        
        elif action == "cancel":
            await query.message.delete()
            
    except Exception as e:
        logger.error(f"Callback handler exception: {e}", exc_info=True)
        await query.message.reply_text(f"❌ 操作异常: {e}")
