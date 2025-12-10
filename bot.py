import os
import json
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web

# ---------------- Environment Variables ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # Replace with your Telegram ID
VIP_FILE = "vip_data.json"

PORT = int(os.environ.get("PORT", 10000))  # Render default port

waiting_for_screenshot = {}  # Format: waiting_for_screenshot[user_id] = "TRC" or "BNB"

# ---------------- Helper Functions ----------------

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
        keyboard = [
            [InlineKeyboardButton("USDT TRC-20", callback_data="vip_trc")],
            [InlineKeyboardButton("USDT-BNB", callback_data="vip_bnb")]
        ]
        await update.message.reply_text(
            "<blockquote>200$ - 1 Month</blockquote>\n\n"
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

# ---------------- Callback Button Handler ----------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "vip_trc":
        waiting_for_screenshot[user_id] = "TRC"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>After depositing to Wallet, send the screenshot below, usually less than 30 minutes to confirm</b>\n\n"
            "<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[user_id] = "BNB"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>After depositing to Wallet, send the screenshot below, usually less than 30 minutes to confirm</b>\n\n"
            "<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "send_screenshot":
        if user_id not in waiting_for_screenshot:
            await query.message.reply_text("Please select a payment method first.")
            return
        await query.message.reply_text("Please send your screenshot now as a photo.")

# ---------------- Photo Handler ----------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("I wasn't expecting a photo. Please press 'Buy VIP' first.")
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()
    payment_type = waiting_for_screenshot[user_id]

    profile_link = f"https://t.me/{user.username}" if user.username else "No username available"
    caption = (
        f"📸 Screenshot Received ({payment_type})\n\n"
        f"👤 User Info\n"
        f"ID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"Name: {user.full_name}\n"
        f"Profile: {profile_link}"
    )

    await context.bot.send_photo(chat_id=OWNER_ID, photo=file.file_id, caption=caption, parse_mode="Markdown")
    del waiting_for_screenshot[user_id]

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]])
    await update.message.reply_text(
        "✅ Payment received. Usually less than 30 minutes to confirm. Contact support if there are issues.",
        reply_markup=keyboard
    )

# ---------------- Admin Commands (add/remove/list/export/import/message) ----------------

# ... Keep all your admin functions exactly as in your code above ...
# (add_vip, remove_vip, vip_list, export_vip, import_vip, message_user)

# ---------------- Background Task ----------------

async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)
        try:
            data = load_vip_data()
            now = datetime.utcnow()
            expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]
            for uid in expired:
                await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ VIP expired for user {uid}")
                del data[uid]
            if expired:
                save_vip_data(data)
        except Exception as e:
            print(f"Error in VIP checker: {e}")

# ---------------- HTTP Server ----------------

async def handle_root(request):
    return web.Response(text="Bot is running!")

async def handle_health(request):
    return web.Response(text="OK")

# ---------------- Main ----------------

if __name__ == "__main__":
    # Telegram Bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("removevip", remove_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("exportvip", export_vip))
    app.add_handler(CommandHandler("importvip", import_vip))
    app.add_handler(CommandHandler("message", message_user))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Run background tasks
    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

        # Start HTTP server on same port
        web_app = web.Application()
        web_app.add_routes([web.get("/", handle_root), web.get("/health", handle_health)])
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
