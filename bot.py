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
from aiohttp import web

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"
PORT = int(os.environ.get("PORT", 10000))

waiting_for_screenshot = {}

# -------------- VIP Helper Functions --------------

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
    return max(0, (expiry - datetime.utcnow()).days)

# -------------- Main Menu --------------

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# -------------- Handlers --------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Press the button below:",
        reply_markup=main_menu()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "Buy VIP":
        keyboard = [
            [InlineKeyboardButton("USDT TRC-20", callback_data="vip_trc")],
            [InlineKeyboardButton("USDT-BNB", callback_data="vip_bnb")]
        ]
        await update.message.reply_text(
            "<blockquote>200$ - 1 Month</blockquote>\n\n"
            "After making a deposit, send the screenshot.\n"
            "Access will be sent automatically.",
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "vip_trc":
        waiting_for_screenshot[user_id] = "TRC"
        await query.message.reply_text(
            "<b>Deposit to the wallet below and send your screenshot.</b>\n\n"
            "<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
            ),
            parse_mode="HTML"
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[user_id] = "BNB"
        await query.message.reply_text(
            "<b>Deposit to the wallet below and send your screenshot.</b>\n\n"
            "<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
            ),
            parse_mode="HTML"
        )

    elif query.data == "send_screenshot":
        await query.message.reply_text("Please send your screenshot as a photo.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("Please select 'Buy VIP' first.")
        return

    photo_file = await update.message.photo[-1].get_file()

    payment_type = waiting_for_screenshot[user_id]
    del waiting_for_screenshot[user_id]

    caption = (
        f"📸 Screenshot Received ({payment_type})\n\n"
        f"ID: {user.id}\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Name: {user.full_name}"
    )

    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=photo_file.file_id,
        caption=caption
    )

    await update.message.reply_text(
        "✅ Payment received. Confirmation in under 30 mins.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]]
        )
    )

# -------------- Admin Commands (unchanged) --------------
# (I removed for brevity, you keep same code here)

# -------------- Background Task --------------

async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)
        try:
            data = load_vip_data()
            now = datetime.utcnow()
            expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]

            for uid in expired:
                await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ VIP expired for {uid}")
                del data[uid]

            if expired:
                save_vip_data(data)

        except Exception as e:
            print("VIP checker error:", e)

# -------------- Health + Root Endpoints --------------

async def handle_root(request):
    return web.Response(text="OK")

async def handle_health(request):
    return web.Response(text="OK")

# -------------- Main Webhook App --------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers...
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

    app.post_init = on_startup

    # Aiohttp server for webhook + health
    aio_app = web.Application()

    aio_app.router.add_get("/", handle_root)
    aio_app.router.add_get("", handle_root)        # important for Render
    aio_app.router.add_get("/health", handle_health)

    print("🚀 Starting Webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        url_path=BOT_TOKEN,
        web_app=aio_app
    )
