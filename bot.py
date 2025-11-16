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

waiting_for_screenshot = {}
# Format: waiting_for_screenshot[user_id] = "TRC" or "BNB"

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
        keyboard = [
            [InlineKeyboardButton("USDT TRC-20", callback_data="vip_trc")],
            [InlineKeyboardButton("USDT-BNB", callback_data="vip_bnb")]
        ]
        await update.message.reply_text(
               "<blockquote>200$ - 1 Month</blockquote>"
            "\n\n"
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

    if query.data == "vip_trc":
        waiting_for_screenshot[user_id] = "TRC"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>Send USDT TRC-20 to the following wallet:</b>\n"
            "<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[user_id] = "BNB"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>Send USDT-BNB to the following wallet:</b>\n"
            "<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


    elif query.data == "send_screenshot":
        if user_id not in waiting_for_screenshot:
            await query.message.reply_text("Please select a payment method first.")
            return
        await query.message.reply_text("Please send your screenshot now as a photo.")

# ---------------- Handle Photos ----------------

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

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
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
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"💎 Your VIP subscription is confirmed!\n"
                f"You now have {days} days access to the VIP channel.\n\n"
                f"Welcome aboard! 🚀"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return
    try:
        user_id = str(context.args[0])
    except IndexError:
        await update.message.reply_text("Usage: /removevip <user_id>")
        return
    data = load_vip_data()
    if user_id not in data:
        await update.message.reply_text(f"❌ User {user_id} is not a VIP.")
        return
    del data[user_id]
    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP removed for user {user_id}.")

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
        report_lines.append(f"{uid} {days_left}")
    await update.message.reply_text("💾 VIP List (ready for import):\n" + "\n".join(report_lines))

async def import_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /importvip <paste your VIP list text>")
        return
    text_data = " ".join(context.args)
    pattern = re.compile(r"(\d{5,20})\D+(\d{1,4})")
    matches = pattern.findall(text_data)
    if not matches:
        await update.message.reply_text("⚠️ No valid VIP entries found in the text.")
        return
    data = load_vip_data()
    added_count = 0
    for uid, days_str in matches:
        try:
            days = int(days_str) + 1
            expiry = datetime.utcnow() + timedelta(days=days)
            data[uid.strip()] = expiry.isoformat()
            added_count += 1
        except ValueError:
            continue
    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP list imported! Added/updated {added_count} users (+1 day each).")

async def message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
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
        await context.bot.send_message(chat_id=user_id, text=message_text)
        await update.message.reply_text(f"✅ Message sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to send message. Error: {e}")

# ---------------- Background Task ----------------

async def check_expired_vips(app):
    while True:
        try:
            await asyncio.sleep(86400)
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
                    report_lines.append(f"{uid} {days_left}")
                await app.bot.send_message(
                    chat_id=OWNER_ID,
                    text="💾 Daily VIP List:\n" + "\n".join(report_lines)
                )
        except Exception as e:
            print(f"Error in VIP checker: {e}")

# ---------------- Health Endpoint ----------------

async def health(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.add_routes([web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# ---------------- Main App ----------------

if __name__ == "__main__":
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
