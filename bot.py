import os
import json
import io
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # Your Telegram ID

VIP_FILE = "vip_data.json"
waiting_for_screenshot = set()


# --- Helper functions ---
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


# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Buy VIP", "📱 My Account"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! Press the button below:", reply_markup=reply_markup)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id in waiting_for_screenshot:
        await update.message.reply_text("Please send your screenshot as a photo, not text.")
        return

    if text == "Buy VIP":
        keyboard = [[InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")]]
        await update.message.reply_text(
            "1 Month - 200$.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif text == "📱 My Account":
        days = get_days_left(user_id)
        if days is None:
            await update.message.reply_text("You don't have an active VIP subscription.")
        elif days > 0:
            await update.message.reply_text(f"💎 You have {days} days of VIP left.")
        else:
            await update.message.reply_text("⚠️ Your VIP has expired.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "confirm_vip":
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "VIP confirmed!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "send_screenshot":
        waiting_for_screenshot.add(user_id)
        await query.message.reply_text("Please send your screenshot now as a photo.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("I wasn't expecting a photo. Please press 'Buy VIP' first.")
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()

    # Send to owner
    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file.file_id,
        caption=f"📸 Screenshot from user {user_id}"
    )

    keyboard = [["Buy VIP", "📱 My Account"]]
    await update.message.reply_text(
        "✅ Screenshot received! Thank you.\nPress 'Buy VIP' again to continue.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    waiting_for_screenshot.remove(user_id)


# --- Admin Commands ---
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        user_id = str(context.args[0])
        days = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addvip <user_id> <days>")
        return

    data = load_vip_data()
    expiry = datetime.utcnow() + timedelta(days=days)
    data[user_id] = expiry.isoformat()
    save_vip_data(data)

    await update.message.reply_text(f"✅ VIP added for user {user_id} ({days} days).")


async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    data = load_vip_data()
    if not data:
        await update.message.reply_text("No VIPs found.")
        return

    report_lines = []
    for uid, expiry in data.items():
        days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
        report_lines.append(f"ID: {uid} | Days left: {days_left}")

    # Send text report
    await update.message.reply_text("\n".join(report_lines))

    # Send JSON backup file
    json_bytes = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
    json_bytes.name = "vip_backup.json"
    await update.message.reply_document(chat_id=OWNER_ID, document=json_bytes, caption="💾 VIP Backup JSON")


async def import_vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    if update.message.document:
        file = await update.message.document.get_file()
        file_path = f"/tmp/{update.message.document.file_name}"
        await file.download_to_drive(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            save_vip_data(data)
            await update.message.reply_text("✅ VIP list imported successfully from file!")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to import: {e}")
        return

    await update.message.reply_text("Please send the VIP JSON file with this command.")


# --- Background Task ---
async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)  # every 24 hours
        data = load_vip_data()
        now = datetime.utcnow()

        # Remove expired VIPs
        expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]
        for uid in expired:
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⚠️ VIP expired for user {uid}"
            )
            del data[uid]
        if expired:
            save_vip_data(data)

        # Send daily report
        if data:
            report_lines = []
            for uid, expiry in data.items():
                days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
                report_lines.append(f"ID: {uid} | Days left: {days_left}")

            # Text report
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text="📊 Daily VIP Report:\n" + "\n".join(report_lines)
            )

            # JSON backup
            json_bytes = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
            json_bytes.name = "vip_backup.json"
            await app.bot.send_document(
                chat_id=OWNER_ID,
                document=json_bytes,
                caption="💾 Daily VIP Backup JSON"
            )


# --- Main App ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("importlist", import_vip_list))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Background VIP checker
    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
