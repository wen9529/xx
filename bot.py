from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, ALIST_HOST, logger
import handlers

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("Bot Token 为空，无法启动！")
        exit(1)

    logger.info(f"正在启动 StreamForge Bot...")
    logger.info(f"Alist 地址: {ALIST_HOST}")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.start))
    app.add_handler(CommandHandler("download", handlers.download_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.menu_handler))
    app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    print("🚀 Bot 已启动！")
    app.run_polling()
