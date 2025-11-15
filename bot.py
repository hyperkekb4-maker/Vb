import os import json import re from datetime import datetime, timedelta import asyncio from telegram import ( Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup ) from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters ) from aiohttp import web

BOT_TOKEN = os.environ.get("BOT_TOKEN") WEBHOOK_URL = os.environ.get("WEBHOOK_URL") OWNER_ID = 8448843919 VIP_FILE = "vip_data.json"

waiting_for_screenshot = set()

---------------- Helper functions ----------------

def load_vip_data(): if os.path.exists(VIP_FILE): with open(VIP_FILE, "r") as f: return json.load(f) return {}

def save_vip_data(data): with open(VIP_FILE, "w") as f: json.dump(data, f, indent=2)

def get_days_left(user_id): data = load_vip_data() if str(user_id) not in data: return None expiry = datetime.fromisoformat(data[str(user_id)]) remaining = (expiry - datetime.utcnow()).days return max(0, remaining)

---------------- Main Menu ----------------

def main_menu(): keyboard = [["Buy VIP", "📱 My Account"]] return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

---------------- Bot Handlers ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "Welcome! Press the button below:", reply_markup=main_menu() )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE): text = update.message.text user = update.message.from_user user_id = user.id

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

---------------- Button Callback ----------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = query.from_user.id

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

---------------- Handle Photos ----------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.message.from_user user_id = user.id

if user_id not in waiting_for_screenshot:
    await update.message.reply_text("I wasn't expecting a photo. Please press 'Buy VIP' first.")
    return

photo_file = update.message.photo[-1]
file = await photo_file.get_file()

profile_link = f"https://t.me/{user.username}" if user.username else "No username available"

caption = (
    f"📸 Screenshot Received

" f"👤 User Info " f"ID: {user.id} " f"Username: @{user.username if user.username else 'N/A'} " f"Name: {user.full_name} " f"Profile: {profile_link}" )

await context.bot.send_photo(
    chat_id=OWNER_ID,
    photo=file.file_id,
    caption=caption,
)

waiting_for_screenshot.remove(user_id)

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Go to my profile", url="https://t.me/HXDM100")]
])

await update.message.reply_text(
    "✅ Payment received. Usually less than 30 minutes to confirm. Contact support if there are issues.",
    reply_markup=keyboard
)

---------------- Admin Commands ----------------

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.from_user.id != OWNER_ID: await update.message.reply_text("You are not authorized.") return

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
            f"💎 Your VIP subscription is confirmed!

" f"You now have {days} days access to the VIP channel.

" f"Welcome aboard! 🚀" ), ) except Exception: pass

async def remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.from_user.id != OWNER_ID: await update.message.reply_text("You are not authorized.") return

try:
    user_id = str(context.args[0])
except (IndexError, ValueError):
    await update.message.reply_text("Usage: /removevip <user_id>")
    return

data = load_vip_data()
if user_id not in data:
    await update.message.reply_text("❌ User not found in VIP list.")
    return

del data[user_id]
save_vip_data(data)

await update.message.reply_text(f"✅ VIP removed for user {user_id}.")

try:
    await context.bot.send_message(
        chat_id=int(user_id),
        text="⚠️ Your VIP subscription has been removed by the administrator."
    )
except Exception:
    pass

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.from_user.id != OWNER_ID: await update.message.reply_text("You are not authorized.") return

data = load_vip_data()
if not data:
    await update.message.reply_text("No VIPs found.")
    return

report_lines = []
for uid, expiry in data.items():
    days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
    report_lines.append(f"ID: {uid} | Days left: {days_left}")

await update.message.reply_text("

".join(report_lines))

async def export_vip(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.from_user.id != OWNER_ID: await update.message.reply_text("You are not authorized.") return

data = load_vip_data()
if not data:
    await update.message.reply_text("No VIPs found.")
    return

report_lines = []
for uid, expiry in data.items():
    days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
    report_lines.append(f"{uid} {days_left}")

await update.message.reply_text("💾 VIP List (ready for import):

" + " ".join(report_lines))

async def import_vip(update: Update, context
