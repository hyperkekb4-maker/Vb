import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bottom menu buttons
    keyboard = [
        ["Buy VIP", "Say Hello"],  # first row
        ["Info", "Help"]           # second row
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! Choose an option from the menu below:", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Buy VIP":
        # Inline buttons inside message
        keyboard = [[InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Hello world! VIP option selected.", reply_markup=reply_markup)

    elif text == "Say Hello":
        keyboard = [[InlineKeyboardButton("Say Hello Again", callback_data="hello_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Hello world!", reply_markup=reply_markup)

    elif text == "Info":
        await update.message.reply_text("This is a demo bot showing menu + inline buttons.")

    elif text == "Help":
        await update.message.reply_text("Use the bottom menu buttons or inline buttons to interact.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_vip":
        await query.message.reply_text("VIP confirmed! Hello world!")

    elif query.data == "hello_again":
        await query.message.reply_text("Hello world again!")

# --- Main app ---

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
