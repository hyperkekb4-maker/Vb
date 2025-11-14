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
OWNER_ID = 8448843919  # Your Telegram ID
VIP_FILE = "vip_data.json"

waiting_for_screenshot = set()

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

# ---------------- Main Menu ---------------- #

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- Bot Handlers ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Press the button below:",
        reply_markup=main_menu()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    user_id = user.id

    # Always reset state if user presses "Buy VIP"
    if text == "Buy VIP":
        if user_id in waiting_for_screenshot:
            waiting_for_screenshot.remove(user_id)

        keyboard = [
            [InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")],
            [InlineKeyboardButton("Confirm VIP 2", callback_data="confirm_vip_2")]
        ]
        await update.message.reply_text(
            "1 Month - 200$.",
            reply_markup=InlineKeyboardMarkup(keyboard)
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

# ---------------- Button Callback ---------------- #

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data in ["confirm_vip", "confirm_vip_2"]:
        await query.message.reply_text("VIP confirmed!")
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "Send your screenshot:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "send_screenshot":
        waiting_for_screenshot.add(user_id)
        await query.message.reply_text("Please send your screenshot now as a photo.")

# ---------------- Handle Photos ---------------- #

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("I wasn't expecting a photo. Please press 'Buy VIP' first.")
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()

    # Build profile link if username exists
    profile_link = f"https://t.me/{user.username}" if user.username else "No username available"

    # Send screenshot + user info to admin
    caption = (
        f"📸 Screenshot Received\n\n"
        f"👤 **User Info**\n"
        f"ID: `{user.id}`\n"
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

    waiting_for_screenshot.remove(user_id)

    # Return menu to user + your profile link
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]
    ])

    await update.message.reply_text(
        "✅ payment received. usually less than 30 minutes its confirmed.you contact the dupport if you had sny problem",
        reply_markup=keyboard
    )

# ---------------- Admin Commands ---------------- #

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

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"💎 Your VIP subscription is confirmed!\n"
                f"You now have **{days} days** access to the VIP channel.\n\n"
                f"Welcome aboard! 🚀"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Couldn't send message to user {user_id}. Error: {e}")

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
    data = load_vip_data()  # Load existing VIPs to not overwrite

    added_count = 0
    for line in lines:
        if ":" not in line:
            continue
        uid, days_str = line.split(":", 1)
        try:
            days = int(days_str) + 1  # Add 1 day to each imported VIP
            expiry = datetime.utcnow() + timedelta(days=days)
            data[uid.strip()] = expiry.isoformat()
            added_count += 1
        except ValueError:
            continue

    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP list imported successfully! Added/updated {added_count} users (+1 day each).")

# ---------------- Message Users by ID ---------------- #

async def message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        if not message_text:
            await update.message.reply_text("Usage: /message <user_id> <message>")
            return
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /message <user_id> <message>")
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message_text
        )
        await update.message.reply_text(f"✅ Message sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to send message to {user_id}. Error: {e}")

# ---------------- Background Task ---------------- #

async def check_expired_vips(app):
    while True:
        try:
            await asyncio.sleep(86400)  # daily
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
                await app.bot.send_message(chat_id=OWNER_ID, text="📊 Daily VIP Report:\n" + "\n".join(report_lines))

        except Exception as e:
            print(f"Error in VIP checker: {e}")

# ---------------- Main App ---------------- #

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("exportvip", export_vip))
    app.add_handler(CommandHandler("importvip", import_vip))
    app.add_handler(CommandHandler("message", message_user))  # New command

    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Callback Query Handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Start background VIP checker
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
