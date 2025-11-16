import os
import json
import re
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web  # For health endpoint

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # Your Telegram ID
VIP_FILE = "vip_data.json"

# Track waiting users with their deposit type
waiting_for_screenshot = {}  # {user_id: deposit_type}

# ---------------- Helper functions ----------------

def load_vip_data():
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    return {}

def save_vip_data(data):
    with open(VIP_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_days_left(user_id):
    data = load_vip_data()
    if str(user_id) not in data:
        return None
    expiry = datetime.fromisoformat(data[str(user_id)])
    remaining = (expiry - datetime.utcnow()).days
    return max(0, remaining)

# ---------------- Main Menu ----------------

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- Bot Handlers ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Press the button below:",
        reply_markup=main_menu()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    user_id = user.id

    if text == "Buy VIP":
        if user_id in waiting_for_screenshot:
            del waiting_for_screenshot[user_id]

        keyboard = [
            [InlineKeyboardButton("USDT TRC-20", callback_data="confirm_vip_trc")],
            [InlineKeyboardButton("USDT-BNB", callback_data="confirm_vip_bnb")]
        ]

        await update.message.reply_text(
            "<code>1 Month – 200$</code>\n"
            "After making a deposit, send us the screenshot,\n"
            "and the access link is sent automatically.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if text == "📱 My Account":
        days = get_days_left(user_id)
        if days is None:
            await update.message.reply_text("You don't have an active VIP subscription.")
        elif days > 0:
            await update.message.reply_text(f"💎 You have {days} days of VIP left.")
        else:
            await update.message.reply_text("⚠️ Your VIP has expired.")
        return

    if user_id in waiting_for_screenshot:
        await update.message.reply_text("Please send your screenshot as a photo, not text.")

# ---------------- Button Callback ----------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "confirm_vip_trc":
        await query.message.reply_text("VIP confirmed for USDT TRC-20!")
        keyboard = [[InlineKeyboardButton("Send TRC-20 Screenshot", callback_data="send_trc_screenshot")]]
        await query.message.reply_text(
            "<code>Send your TRC-20 screenshot:</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "confirm_vip_bnb":
        await query.message.reply_text("VIP confirmed for USDT-BNB!")
        keyboard = [[InlineKeyboardButton("Send BNB Screenshot", callback_data="send_bnb_screenshot")]]
        await query.message.reply_text(
            "<code>Send your BNB screenshot:</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "send_trc_screenshot":
        waiting_for_screenshot[user_id] = "TRC-20"
        await query.message.reply_text("Please send your TRC-20 screenshot now as a photo.")

    elif query.data == "send_bnb_screenshot":
        waiting_for_screenshot[user_id] = "BNB"
        await query.message.reply_text("Please send your BNB screenshot now as a photo.")

# ---------------- Handle Photos ----------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("I wasn't expecting a photo. Please press 'Buy VIP' first.")
        return

    deposit_type = waiting_for_screenshot[user_id]
    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()

    profile_link = f"https://t.me/{user.username}" if user.username else "No username available"

    caption = (
        f"📸 Screenshot Received ({deposit_type})\n\n"
        f"👤 User Info\n"
        f"ID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"Name: {user.full_name}\n"
        f"Profile: {profile_link}"
    )

    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file.file_id,
        caption=caption,
        parse_mode="Markdown"
    )

    del waiting_for_screenshot[user_id]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]
    ])

    await update.message.reply_text(
        "✅ Payment received. Usually less than 30 minutes to confirm. Contact support if there are issues.",
        reply_markup=keyboard
    )

# ---------------- Admin Commands ----------------
# (Keep all admin commands as in your original code)
# add_vip, remove_vip, vip_list, export_vip, import_vip, message_user
# ---------------- Background Task ----------------
# check_expired_vips, health, start_health_server (same as before)
# ---------------- Main App ----------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("removevip", remove_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("exportvip", export_vip))
    app.add_handler(CommandHandler("importvip", import_vip))
    app.add_handler(CommandHandler("message", message_user))

    # Handlers
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))
        asyncio.create_task(start_health_server())

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
