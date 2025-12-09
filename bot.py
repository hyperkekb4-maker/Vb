import os
import json
import re
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://your-app.onrender.com
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"

waiting_for_screenshot = {}

# Optional health check endpoint (for Render or uptime monitoring)
async def health(request):
    return web.Response(text="OK")

# Initialize the Telegram bot
app = Application.builder().token(BOT_TOKEN).build()

# If you want a health endpoint, create an aiohttp server alongside PTB
async def run_servers():
    # Aiohttp server for health checks
    web_app = web.Application()
    web_app.router.add_get("/health", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8443)))
    await site.start()

    # Start the bot webhook server
    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    await app.updater.idle()

# Entry point
if __name__ == "__main__":
    asyncio.run(run_servers())


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


# ---------------- Menus ----------------

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
            "<b>Subscription Price:</b>\n"
            "<blockquote>200$ - 1 Month</blockquote>\n\n"
            "<b>Select your payment option:</b>",
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


# ---------------- Button Handler ----------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "vip_trc":
        waiting_for_screenshot[user_id] = "TRC"
        await query.message.delete()

        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "<b>After depositing, send the screenshot below.</b>\n\n"
                "<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[user_id] = "BNB"
        await query.message.delete()

        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "<b>After depositing, send the screenshot below.</b>\n\n"
                "<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>"
            ),
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
        await update.message.reply_text("I wasn't expecting a photo. Press 'Buy VIP' first.")
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()

    payment_type = waiting_for_screenshot[user_id]
    profile_link = f"https://t.me/{user.username}" if user.username else "No username"

    caption = (
        f"📸 Screenshot Received ({payment_type})\n\n"
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
        "✅ Payment received. Confirmation usually under 30 minutes.",
        reply_markup=keyboard
    )


# ---------------- Admin Commands ----------------

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    try:
        user_id = str(context.args[0])
        days = int(context.args[1])
    except:
        return await update.message.reply_text("Usage: /addvip <user_id> <days>")

    data = load_vip_data()
    expiry = datetime.utcnow() + timedelta(days=days)
    data[user_id] = expiry.isoformat()
    save_vip_data(data)

    await update.message.reply_text(f"VIP added for {user_id} ({days} days).")
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"💎 Your VIP subscription is confirmed for {days} days!"
        )
    except:
        pass


async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")

    try:
        user_id = str(context.args[0])
    except:
        return await update.message.reply_text("Usage: /removevip <user_id>")

    data = load_vip_data()
    if user_id not in data:
        return await update.message.reply_text("User not VIP.")

    del data[user_id]
    save_vip_data(data)

    await update.message.reply_text(f"VIP removed for {user_id}.")


async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    data = load_vip_data()
    if not data:
        return await update.message.reply_text("No VIPs.")
    lines = [f"{uid} | {get_days_left(uid)} days left" for uid in data]
    await update.message.reply_text("\n".join(lines))


# ---------------- Background Task ----------------

async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)
        data = load_vip_data()
        now = datetime.utcnow()

        expired = [uid for uid, exp in data.items()
                   if datetime.fromisoformat(exp) <= now]

        for uid in expired:
            await app.bot.send_message(chat_id=OWNER_ID,
                                       text=f"⚠️ VIP expired for user {uid}")
            del data[uid]

        if expired:
            save_vip_data(data)


# ---------------- Health Route ----------------

async def health(request):
    return web.Response(text="OK")


# ---------------- Main ----------------

if __name__ == "__main__":

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Inject /health into webhook server
    app.web_app.router.add_get("/health", health)

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("removevip", remove_vip))
    app.add_handler(CommandHandler("viplist", vip_list))

    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

    app.post_init = on_startup

    print("🚀 Running in Webhook mode with /health enabled...")

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
