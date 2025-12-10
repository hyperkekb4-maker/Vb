import os
import json
from datetime import datetime, timedelta
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
OWNER_ID = 8448843919
VIP_FILE = "vip_data.json"

waiting_for_screenshot = {}

# ---------------- Helper Functions ----------------
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

def main_menu():
    keyboard = [["Buy VIP", "📱 My Account"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Press the button below:",
        reply_markup=main_menu()
    )

# (Other handlers remain the same, like handle_text, handle_photo, button_callback, add_vip, remove_vip, vip_list)
# ---------------- Background Task ----------------
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

# ---------------- Health Route ----------------
async def health(request):
    return web.Response(text="OK")

# ---------------- Main ----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    # Add other handlers here...

    # Background tasks
    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

    app.post_init = on_startup

    # ---------------- Start separate aiohttp server for /health ----------------
    async def run_health():
        health_app = web.Application()
        health_app.add_routes([web.get('/health', health)])
        runner = web.AppRunner(health_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
        await site.start()
        print("✅ Health server running on /health")

    asyncio.get_event_loop().create_task(run_health())

    print("🚀 Bot is running via webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
