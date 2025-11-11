import os
import json
import base64
import requests
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # Your Telegram ID

VIP_FILE = "vip_data.json"
waiting_for_screenshot = set()

# --- GitHub Config ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO_OWNER = "your-username"  # replace with your GitHub username
GITHUB_REPO_NAME = "your-repo-name"  # replace with your GitHub repo name
VIP_FILE_PATH = VIP_FILE  # path inside your repo


# --- Helper functions ---
def push_to_github(data):
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{VIP_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    # Check if file exists to get SHA
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content = base64.b64encode(json.dumps(data).encode()).decode()
    payload = {
        "message": "Update VIP data",
        "content": content,
        "sha": sha
    }

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code not in [200, 201]:
        print("⚠️ Failed to push VIP data to GitHub:", r.text)


def load_vip_data():
    # Try to load from GitHub first
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{VIP_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json().get("content")
        if content:
            data = json.loads(base64.b64decode(content).decode())
            return data

    # Fallback to local file
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    return {}


def save_vip_data(data):
    # Save locally
    with open(VIP_FILE, "w") as f:
        json.dump(data, f)
    # Push to GitHub
    push_to_github(data)


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
            "VIP option selected.",
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


async def reduce_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        user_id = str(context.args[0])
        days = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reducevip <user_id> <days>")
        return

    data = load_vip_data()
    if user_id not in data:
        await update.message.reply_text("User does not have VIP.")
        return

    expiry = datetime.fromisoformat(data[user_id]) - timedelta(days=days)
    if expiry <= datetime.utcnow():
        del data[user_id]
        await update.message.reply_text(f"⚠️ VIP removed for user {user_id}.")
    else:
        data[user_id] = expiry.isoformat()
        await update.message.reply_text(f"✅ VIP reduced by {days} days for user {user_id}.")

    save_vip_data(data)


# --- Background Task ---
async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)  # check every 24 hours
        data = load_vip_data()
        now = datetime.utcnow()
        expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]
        for uid in expired:
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⚠️ VIP expired for user {uid}"
            )
            del data[uid]
        if expired:
            save_vip_data(data)


# --- Main App ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("reducevip", reduce_vip))
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
