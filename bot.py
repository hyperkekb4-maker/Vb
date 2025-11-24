import os
import json
import asyncio
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web

# ----------------- ENV -----------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"
PORT = int(os.environ.get("PORT", 10000))

waiting_for_screenshot = {}

# ----------------- VIP SYSTEM -----------------

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
    return max(0, (expiry - datetime.utcnow()).days)

# ----------------- UI -----------------

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ----------------- HANDLERS -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome!", reply_markup=main_menu())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "Buy VIP":
        keyboard = [
            [InlineKeyboardButton("USDT TRC-20", callback_data="vip_trc")],
            [InlineKeyboardButton("USDT-BNB", callback_data="vip_bnb")]
        ]
        await update.message.reply_text(
            "<b>200$ - 1 Month</b>\n\nSend screenshot after deposit.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if text == "📱 My Account":
        days = get_days_left(user_id)
        if days is None:
            await update.message.reply_text("❌ No VIP.")
        elif days > 0:
            await update.message.reply_text(f"💎 {days} days left.")
        else:
            await update.message.reply_text("⚠️ VIP expired.")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "vip_trc":
        waiting_for_screenshot[uid] = "TRC"
        await query.message.reply_text(
            "<b>Deposit to:</b>\n<code>TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
            )
        )

    elif query.data == "vip_bnb":
        waiting_for_screenshot[uid] = "BNB"
        await query.message.reply_text(
            "<b>Deposit to:</b>\n<code>0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Send Screenshot", callback_data="send_screenshot")]]
            )
        )

    elif query.data == "send_screenshot":
        await query.message.reply_text("Send your screenshot now.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    uid = user.id

    if uid not in waiting_for_screenshot:
        await update.message.reply_text("Go to 'Buy VIP' first.")
        return

    payment_type = waiting_for_screenshot[uid]
    del waiting_for_screenshot[uid]

    file_id = update.message.photo[-1].file_id

    caption = (
        f"📸 Screenshot ({payment_type})\n"
        f"ID: {uid}\n"
        f"User: @{user.username or 'N/A'}\n"
        f"Name: {user.full_name}"
    )

    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file_id,
        caption=caption
    )

    await update.message.reply_text(
        "✅ Payment received. Confirming...",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("My Profile", url="https://t.me/HXDM100")]]
        )
    )

# ----------------- VIP EXPIRATION TASK -----------------

async def vip_checker(bot):
    while True:
        await asyncio.sleep(86400)
        data = load_vip_data()
        now = datetime.utcnow()

        expired = [uid for uid, exp in data.items() if datetime.fromisoformat(exp) <= now]

        for uid in expired:
            try:
                await bot.send_message(OWNER_ID, f"⚠️ VIP expired: {uid}")
            except:
                pass
            del data[uid]

        if expired:
            save_vip_data(data)

# ----------------- AIOHTTP ROUTES -----------------

async def handle_root(request):
    return web.Response(text="OK")

async def handle_health(request):
    return web.Response(text="OK")

# ----------------- MAIN (MANUAL WEBHOOK SERVER) -----------------

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    async def on_start(app):
        asyncio.create_task(vip_checker(app.bot))

    application.post_init = on_start

    # ---- AIOHTTP WEB SERVER ----
    web_app = web.Application()

    # Telegram webhook handler from PTB
    webhook_handler = application.webhook_handler()

    web_app.router.add_post(f"/{BOT_TOKEN}", webhook_handler)
    web_app.router.add_get("/", handle_root)
    web_app.router.add_get("/health", handle_health)

    # Set Telegram webhook on startup
    async def set_webhook(_):
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

    web_app.on_startup.append(set_webhook)

    # Start aiohttp
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    print("🚀 Webhook server started!")
    await site.start()

    # Required PTB startup
    await application.initialize()
    await application.start()

    # Keep running
    await application.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
