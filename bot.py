import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Buy VIP", callback_data="buy_vip")],
        [InlineKeyboardButton("Say Hello", callback_data="say_hello")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy_vip":
        keyboard = [[InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send a new message instead of replacing
        await query.message.reply_text("Hello world! VIP option selected.", reply_markup=reply_markup)

    elif query.data == "say_hello":
        keyboard = [[InlineKeyboardButton("Say Hello Again", callback_data="hello_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Hello world!", reply_markup=reply_markup)

    elif query.data == "confirm_vip":
        await query.message.reply_text("VIP confirmed! Hello world!")

    elif query.data == "hello_again":
        await query.message.reply_text("Hello world again!")

# --- Main app ---

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
