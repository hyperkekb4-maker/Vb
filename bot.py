import os
import json
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,  # ✅ lowercase for v20+
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
        # ✅ 100% copyable plain text message
        await update.message.reply_text(
            "Hello 👋\n\n1 Month - 200$.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            protect_content=False  # ensure copy/forward works
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

    # Send screenshot to admin
    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file.file_id,
        caption=f"📸 Screenshot from user {user_id}"
    )

    # Keyboard with button linking to your admin profile
    keyboard = [[InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ Screenshot received! Thank you.\nPress 'Buy VIP' again to continue.",
        reply_markup=reply_markup
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

    await update.message.reply_text("\n".join(report_lines))


async def export_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        report_lines.append(f"{uid}:{days_left}")

    await update.message.reply_text("💾 VIP List:\n" + "\n".join(report_lines))


async def import_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /importvip <paste your VIP list text>")
        return

    text_data = " ".join(context.args).replace("\\n", "\n")
    lines = text_data.strip().splitlines()
    data = {}
    for line in lines:
        if ":" not in line:
            continue
        uid, days_str = line.split(":", 1)
        try:
            days = int(days_str)
            expiry = datetime.utcnow() + timedelta(days=days)
            data[uid.strip()] = expiry.isoformat()
        except ValueError:
            continue

    save_vip_data(data)
    await update.message.reply_text("✅ VIP list imported successfully!")


# --- Background Task ---
async def check_expired_vips(app):
    while True:
        try:
            await asyncio.sleep(86400)  # every 24 hours
            data = load_vip_data()
            now = datetime.utcnow()

            expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]
            for uid in expired:
                await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ VIP expired for user {uid}")
                del data[uid]
            if expired:
                save_vip_data(data)

            if data:
                report_lines = []
                for uid, expiry in data.items():
                    days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
                    report_lines.append(f"ID: {uid} | Days left: {days_left}")

                await app.bot.send_message(
                    chat_id=OWNER_ID,
                    text="📊 Daily VIP Report:\n" + "\n".join(report_lines)
                )

        except Exception as e:
            print(f"Error in VIP checker: {e}")


# --- Main App ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("exportvip", export_vip))
    app.add_handler(CommandHandler("importvip", import_vip))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

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
