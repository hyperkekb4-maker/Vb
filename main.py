import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import nest_asyncio

nest_asyncio.apply()  # Allows nested asyncio loops if needed

# ---------------- Dummy HTTP Server for Render ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), Handler)
    print(f"🌐 HTTP server listening on port {port} (for Render port detection)")
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# ---------------- Bot Handlers (fill these in) ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Make sure your Render env has this

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is running.")

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("VIP added!")

async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("VIP removed!")

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("VIP list here!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nice photo!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Button clicked!")

# Example background task
async def vip_checker(application):
    while True:
        print("Checking VIPs...")
        await asyncio.sleep(60)  # every 60 seconds

# ---------------- Main Bot ----------------
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addvip", add_vip))
    application.add_handler(CommandHandler("removevip", remove_vip))
    application.add_handler(CommandHandler("viplist", vip_list))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Background task
    application.create_task(vip_checker(application))

    print("🤖 Bot started in POLLING mode...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
