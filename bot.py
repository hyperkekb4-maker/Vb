import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "False").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

# Flask app (used only for webhook mode)
app = Flask(__name__)

# --- Telegram Bot setup ---
application = Application.builder().token(BOT_TOKEN).build()


# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Buy VIP", callback_data="buy_vip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Click the button:", reply_markup=reply_markup)


# Button callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "buy_vip":
        await query.message.reply_text("Hello world!")


# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_callback))


# --- Flask route for Telegram Webhook ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200


if __name__ == "__main__":
    if WEBHOOK_MODE:
        # --- Webhook Mode (for Render Web Service) ---
        print("🚀 Starting bot in WEBHOOK mode...")
        application.bot.delete_webhook(drop_pending_updates=True)
        application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=PORT)
    else:
        # --- Polling Mode (for Render Background Worker or Local Testing) ---
        print("🤖 Starting bot in POLLING mode...")
        application.run_polling()
