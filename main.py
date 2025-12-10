import os
import json
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")             
OWNER_ID = 8448843919                               
VIP_FILE = "vip_data.json"

waiting_for_screenshot = {}


# ---------------- Helper functions -----------------

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

    if query.data.startswith("vip_"):
        waiting_for_screenshot[user_id] = query.data.split("_")[1].upper()
        await query.message.delete()

        address = "TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw" if query.data == "vip_trc" \
            else "0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003"

        keyboard = [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"<b>After depositing, send the screenshot below.</b>\n\n"
                 f"<code>{address}</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "send_screenshot":
        if user_id not in waiting_for_screenshot:
            return await query.message.reply_text("Please select a payment method first.")
        await query.message.reply_text("Please send your screenshot now as a photo.")


# ---------------- Photo Handler ----------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in waiting_for_screenshot:
        return await update.message.reply_text("I wasn't expecting a photo. Press 'Buy VIP' first.")

    photo = update.message.photo[-1]

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
        photo=photo.file_id,
        caption=caption
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
    data[user_id] = (datetime.utcnow() + timedelta(days=days)).isoformat()
    save_vip_data(data)

    await update.message.reply_text(f"VIP added for {user_id} ({days} days).")
    try:
        await context.bot.send_message(int(user_id), f"💎 Your VIP subscription is confirmed for {days} days!")
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


# ---------------- Background VIP Checker ----------------

async def vip_checker(application):
    await application.wait_until_ready()  # ensures bot is started
    while True:
        await asyncio.sleep(86400)

        data = load_vip_data()
        now = datetime.utcnow()

        expired = [uid for uid, exp in data.items()
                   if datetime.fromisoformat(exp) <= now]

        for uid in expired:
            await application.bot.send_message(OWNER_ID, f"⚠ VIP expired for user {uid}")
            del data[uid]

        if expired:
            save_vip_data(data)


# ---------------- POLLING MODE MAIN ----------------

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addvip", add_vip))
    application.add_handler(CommandHandler("removevip", remove_vip))
    application.add_handler(CommandHandler("viplist", vip_list))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Background task
    asyncio.create_task(vip_checker(application))

    print("🤖 Bot started in POLLING mode...")
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
