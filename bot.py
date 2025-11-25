import os
import json
import re
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from aiohttp import web

# ----------------- CONFIG -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"
waiting_for_screenshot = {}

# ----------------- VIP DATA -----------------
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

# ----------------- MAIN MENU -----------------
def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ----------------- HANDLERS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Press a button below:", reply_markup=main_menu())

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
            "<b>200$ - 1 Month</b>\n\nSend screenshot after deposit. Access is granted automatically upon confirmation.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

if text == "📱 My Account":
    days = get_days_left(user_id)
    if days is None:
        await update.message.reply_text("❌ No VIP subscription.")
    elif days > 0:
        await update.message.reply_text(
            f"💎 VIP active\n"
            f"⏳ {days} days remaining"
        )
    else:
        await update.message.reply_text("⚠️ Your VIP has expired.")
    return


    if user_id in waiting_for_screenshot:
        await update.message.reply_text("Please send your screenshot as a photo, not text.")

# ----------------- BUTTON CALLBACK -----------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "vip_trc":
        waiting_for_screenshot[user_id] = "TRC"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>Deposit to:</b>\n<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>\n\nSend screenshot after deposit.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[user_id] = "BNB"
        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
        await query.message.reply_text(
            "<b>Deposit to:</b>\n<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>\n\nSend screenshot after deposit.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "send_screenshot":
        if user_id not in waiting_for_screenshot:
            await query.message.reply_text("Please select a payment method first.")
            return
        await query.message.reply_text("Send your screenshot now as a photo.")

# ----------------- HANDLE PHOTOS -----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        await update.message.reply_text("Go to 'Buy VIP' first.")
        return

    photo_file = update.message.photo[-1]
    file = await photo_file.get_file()
    payment_type = waiting_for_screenshot[user_id]
    del waiting_for_screenshot[user_id]

    profile_link = f"https://t.me/{user.username}" if user.username else "No username"

    caption = (
        f"📸 Screenshot Received ({payment_type})\n"
        f"👤 ID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"Name: {user.full_name}\n"
        f"Profile: {profile_link}"
    )

    await context.bot.send_photo(chat_id=OWNER_ID, photo=file.file_id, caption=caption)
    await update.message.reply_text(
        "✅ Payment received. Usually less than 30 minutes to confirm.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]])
    )

# ----------------- ADMIN COMMANDS -----------------
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    try:
        user_id = str(context.args[0])
        days = int(context.args[1])
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /addvip <user_id> <days>")

    data = load_vip_data()
    expiry = datetime.utcnow() + timedelta(days=days)
    data[user_id] = expiry.isoformat()
    save_vip_data(data)

    await update.message.reply_text(f"✅ VIP added for user {user_id} ({days} days).")
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"💎 Your VIP subscription is confirmed! You now have {days} days access to VIP."
        )
    except:
        pass

async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    try:
        user_id = str(context.args[0])
    except IndexError:
        return await update.message.reply_text("Usage: /removevip <user_id>")
    data = load_vip_data()
    if user_id not in data:
        return await update.message.reply_text(f"❌ User {user_id} is not a VIP.")
    del data[user_id]
    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP removed for user {user_id}.")

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    data = load_vip_data()
    if not data:
        return await update.message.reply_text("No VIPs found.")
    lines = [f"ID: {uid} | Days left: {(datetime.fromisoformat(exp) - datetime.utcnow()).days}" for uid, exp in data.items()]
    await update.message.reply_text("\n".join(lines))

async def export_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    data = load_vip_data()
    lines = [f"{uid} {(datetime.fromisoformat(exp) - datetime.utcnow()).days}" for uid, exp in data.items()]
    await update.message.reply_text("💾 VIP List:\n" + "\n".join(lines))

async def import_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    if not context.args:
        return await update.message.reply_text("Usage: /importvip <VIP list>")
    text_data = " ".join(context.args)
    pattern = re.compile(r"(\d{5,20})\D+(\d{1,4})")
    matches = pattern.findall(text_data)
    if not matches:
        return await update.message.reply_text("⚠️ No valid VIP entries found.")
    data = load_vip_data()
    added_count = 0
    for uid, days_str in matches:
        try:
            days = int(days_str) + 1
            data[uid.strip()] = (datetime.utcnow() + timedelta(days=days)).isoformat()
            added_count += 1
        except:
            continue
    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP imported! Added/updated {added_count} users.")

async def message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorized.")
    try:
        user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        if not message_text:
            return await update.message.reply_text("Usage: /message <user_id> <message>")
    except:
        return await update.message.reply_text("Usage: /message <user_id> <message>")
    try:
        await context.bot.send_message(chat_id=user_id, text=message_text)
        await update.message.reply_text(f"✅ Message sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed: {e}")

# ----------------- VIP CHECKER -----------------
async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)
        data = load_vip_data()
        now = datetime.utcnow()
        expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]
        for uid in expired:
            await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ VIP expired for user {uid}")
            del data[uid]
        if expired:
            save_vip_data(data)

# ----------------- HEALTH ENDPOINT -----------------
async def health(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.add_routes([web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# ----------------- RUN BOT -----------------
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

    # Background tasks
    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))
        asyncio.create_task(start_health_server())

    app.post_init = on_startup

    print("🚀 Starting bot...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
