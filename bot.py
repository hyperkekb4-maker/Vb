import os
import json
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
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"

waiting_for_screenshot = set()
last_bot_message = {}   # <----- NEW

# ---------------- Helper functions ---------------- #

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

# ------------- Clean message sender (Deletes old bot message) ------------- #

async def send_clean_message(chat_id, text, context, reply_markup=None):
    # delete previous message
    if chat_id in last_bot_message:
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=last_bot_message[chat_id]
            )
        except:
            pass

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )

    last_bot_message[chat_id] = sent.message_id

# ---------------- Main Menu ---------------- #

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- Bot Handlers ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_clean_message(
        chat_id=update.message.chat_id,
        text="Welcome! Press the button below:",
        context=context,
        reply_markup=main_menu()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # Buy VIP
    if text == "Buy VIP":
        if user_id in waiting_for_screenshot:
            waiting_for_screenshot.remove(user_id)

        keyboard = [
            [InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")],
            [InlineKeyboardButton("Confirm VIP 2", callback_data="confirm_vip_2")]
        ]

        await send_clean_message(
            chat_id=user_id,
            text="1 Month - 200$.",
            context=context,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # My Account
    if text == "📱 My Account":
        days = get_days_left(user_id)
        if days is None:
            msg = "You don't have an active VIP subscription."
        elif days > 0:
            msg = f"💎 You have {days} days of VIP left."
        else:
            msg = "⚠️ Your VIP has expired."

        await send_clean_message(user_id, msg, context)
        return

    # Wrong content
    if user_id in waiting_for_screenshot:
        await send_clean_message(
            user_id,
            "Please send your screenshot as a photo, not text.",
            context
        )

# ---------------- Button Callback ---------------- #

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Confirm VIP buttons
    if query.data in ["confirm_vip", "confirm_vip_2"]:
        await send_clean_message(user_id, "VIP confirmed!", context)

        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]

        await send_clean_message(
            user_id,
            "Send your screenshot:",
            context,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Send screenshot button
    elif query.data == "send_screenshot":
        waiting_for_screenshot.add(user_id)
        await send_clean_message(
            user_id,
            "Please send your screenshot now as a photo.",
            context
        )

# ---------------- Handle Photos ---------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in waiting_for_screenshot:
        await send_clean_message(
            user_id,
            "I wasn't expecting a photo. Please press 'Buy VIP' first.",
            context
        )
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()

    # Send screenshot to admin
    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file.file_id,
        caption=f"📸 Screenshot from user {user_id}"
    )

    waiting_for_screenshot.remove(user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]
    ])

    await send_clean_message(
        user_id,
        "✅ Screenshot received! The VIP flow has restarted.",
        context,
        reply_markup=keyboard
    )

# ---------------- Admin Commands ---------------- #

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await send_clean_message(update.message.chat_id, "Not authorized.", context)

    try:
        user_id = str(context.args[0])
        days = int(context.args[1])
    except:
        return await send_clean_message(update.message.chat_id, "Usage: /addvip <user_id> <days>", context)

    data = load_vip_data()
    expiry = datetime.utcnow() + timedelta(days=days)
    data[user_id] = expiry.isoformat()
    save_vip_data(data)

    await send_clean_message(update.message.chat_id, f"VIP added for {user_id} ({days} days).", context)

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"💎 Your VIP subscription is confirmed!\nYou now have **{days} days** access.",
            parse_mode="Markdown"
        )
    except:
        pass

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await send_clean_message(update.message.chat_id, "Not authorized.", context)

    data = load_vip_data()
    if not data:
        return await send_clean_message(update.message.chat_id, "No VIPs found.", context)

    report = "\n".join(
        f"ID: {uid} | Days left: {(datetime.fromisoformat(expiry) - datetime.utcnow()).days}"
        for uid, expiry in data.items()
    )

    await send_clean_message(update.message.chat_id, report, context)

async def export_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await send_clean_message(update.message.chat_id, "Not authorized.", context)

    data = load_vip_data()
    if not data:
        return await send_clean_message(update.message.chat_id, "No VIPs found.", context)

    report = "\n".join(
        f"{uid}:{(datetime.fromisoformat(expiry) - datetime.utcnow()).days}"
        for uid, expiry in data.items()
    )

    await send_clean_message(update.message.chat_id, "💾 VIP List:\n" + report, context)

async def import_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await send_clean_message(update.message.chat_id, "Not authorized.", context)

    if not context.args:
        return await send_clean_message(update.message.chat_id, "Usage: /importvip <data>", context)

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
        except:
            continue

    save_vip_data(data)
    await send_clean_message(update.message.chat_id, "VIP list imported!", context)

# ---------------- Background VIP Checker ---------------- #

async def check_expired_vips(app):
    while True:
        try:
            await asyncio.sleep(86400)
            data = load_vip_data()
            now = datetime.utcnow()
            expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]

            for uid in expired:
                del data[uid]
                await app.bot.send_message(chat_id=OWNER_ID, text=f"VIP expired for {uid}")

            if expired:
                save_vip_data(data)

        except Exception as e:
            print("VIP CHECK ERROR:", e)

# ---------------- Main App ---------------- #

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
