import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = int(os.environ.get("OWNER_ID"))  # Your Telegram ID to receive screenshots

# Track which users are sending screenshots
waiting_for_screenshot = set()

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Buy VIP"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! Press the button below:", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id in waiting_for_screenshot:
        await update.message.reply_text("Please send a screenshot, not text.")
        return

    if text == "Buy VIP":
        keyboard = [[InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Hello world! VIP option selected.", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "confirm_vip":
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("VIP confirmed! Hello world!", reply_markup=reply_markup)

    elif query.data == "send_screenshot":
        waiting_for_screenshot.add(user_id)
        await query.message.reply_text("Please send your screenshot now as a photo.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("I wasn't expecting a photo. Press the button first.")
        return

    # Forward the photo to OWNER_ID
    photo_file = update.message.photo[-1]
    await photo_file.get_file().download_to_drive(f"/tmp/{photo_file.file_id}.jpg")
    await context.bot.send_photo(chat_id=OWNER_ID, photo=open(f"/tmp/{photo_file.file_id}.jpg", "rb"))
    
    await update.message.reply_text("Screenshot received! Thank you.")
    waiting_for_screenshot.remove(user_id)

# --- Main app ---

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
