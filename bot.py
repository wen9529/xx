from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
import handlers

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.start))
    app.add_handler(CommandHandler("download", handlers.download_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.menu_handler))
    app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    print("🚀 Bot 已启动！代码已重构为模块化结构。")
    app.run_polling()
