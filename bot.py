from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from config import BOT_TOKEN, ALIST_HOST, logger
import handlers
import traceback
import html
import json

async def global_error_handler(update, context):
    """
    全局错误处理器：捕获所有未处理的异常并发送给用户。
    """
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # 获取异常堆栈
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    # 构建错误消息
    error_summary = str(context.error)
    
    # 打印到控制台
    print(f"❌ [Global Error] {error_summary}", flush=True)

    # 尝试回复用户
    if update and update.effective_message:
        try:
            # 截取最后 2000 个字符防止消息过长
            short_tb = tb_string[-2000:] if len(tb_string) > 2000 else tb_string
            
            message = (
                f"❌ **系统发生严重错误**\n\n"
                f"⚠️ **异常信息**: `{html.escape(error_summary)}`\n\n"
                f"📋 **详细日志**:\n"
                f"```python\n{short_tb}\n```"
            )
            await update.effective_message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send error report to user: {e}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("Bot Token 为空，无法启动！")
        exit(1)

    logger.info(f"🚀 正在启动 StreamForge Bot...")
    logger.info(f"📡 Alist 地址: {ALIST_HOST}")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # 注册全局错误处理器
    app.add_error_handler(global_error_handler)
    
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.start))
    app.add_handler(CommandHandler("download", handlers.download_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.menu_handler))
    app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    print("✅ Bot 已成功运行，正在监听消息...", flush=True)
    
    # 允许所有更新类型，并丢弃 pending updates 避免启动时处理旧消息导致逻辑错误
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
