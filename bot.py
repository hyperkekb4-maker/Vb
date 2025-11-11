import os
import json
import io
from datetime import datetime, timedelta
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # Your Telegram ID
ADMIN_PROFILE = "https://t.me/HXDM100"  # link that Send Screenshot button opens

VIP_FILE = "vip_data.json"

# --- Helpers ---
def load_vip_data():
    """Return dict: {name: expiry_iso_str}"""
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_vip_data(data):
    with open(VIP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_possible_value(value):
    """Accept either ISO datetime string or integer-days."""
    try:
        days = int(value)
        expiry = datetime.utcnow() + timedelta(days=days)
        return expiry.isoformat()
    except Exception:
        try:
            _ = datetime.fromisoformat(value)
            return value
        except Exception:
            return None

def get_days_left(name):
    data = load_vip_data()
    if name not in data:
        return None
    try:
        expiry = datetime.fromisoformat(data[name])
    except Exception:
        return None
    remaining = (expiry - datetime.utcnow()).days
    return max(0, remaining)

# --- Bot handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Buy VIP", "📱 My Account"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! Press the button below:", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Buy VIP":
        keyboard = [[InlineKeyboardButton("Confirm VIP", callback_data="confirm_vip")]]
        await update.message.reply_text("1 Month - 200$.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if text == "📱 My Account":
        await update.message.reply_text(
            "To check your VIP days, please tell me the name used for your VIP (or ask admin).\n"
            "If you already have a VIP name stored, admin can tell you your days left."
        )
        return

# --- Buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_vip":
        # ✅ Fixed: button now opens your Telegram profile link
        keyboard = [[InlineKeyboardButton("Send Screenshot", url=ADMIN_PROFILE)]]
        await query.message.reply_text(
            "VIP confirmed!\nPlease send your payment screenshot to the admin via the button below 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- Admin commands ---
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /addvip <name> <days>"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    try:
        name = context.args[0]
        days = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addvip <name> <days>\nExample: /addvip John 30")
        return

    data = load_vip_data()
    expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
    data[name] = expiry
    save_vip_data(data)
    await update.message.reply_text(f"✅ VIP added for **{name}** — {days} days (until {expiry}).", parse_mode="Markdown")

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual report: text + JSON backup"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    data = load_vip_data()
    if not data:
        await update.message.reply_text("No VIPs found.")
        return

    report_lines = []
    for name, expiry in data.items():
        try:
            days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
            days_left = max(0, days_left)
        except Exception:
            days_left = "unknown"
        report_lines.append(f"{name} — {days_left} days left")

    await update.message.reply_text("📊 VIP Report:\n" + "\n".join(report_lines))

    # JSON backup file
    json_bytes = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    json_bytes.name = "vip_backup.json"
    await update.message.reply_document(chat_id=OWNER_ID, document=json_bytes, caption="💾 VIP Backup JSON")

async def backup_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual backup (only JSON file)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    data = load_vip_data()
    if not data:
        await update.message.reply_text("No VIP data to back up.")
        return

    json_bytes = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    json_bytes.name = "vip_backup.json"
    await update.message.reply_document(chat_id=OWNER_ID, document=json_bytes, caption="💾 Manual VIP Backup JSON")

async def import_vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import VIP list from JSON file"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized.")
        return

    if not update.message.document:
        await update.message.reply_text("Please attach the VIP JSON file with this command.")
        return

    doc = update.message.document
    file = await doc.get_file()
    tmp_path = f"/tmp/{doc.file_name}"
    await file.download_to_drive(tmp_path)

    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            incoming = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"Failed to read JSON file: {e}")
        return

    normalized = {}
    now = datetime.utcnow()
    for name, val in incoming.items():
        if isinstance(val, int):
            expiry = (now + timedelta(days=val)).isoformat()
            normalized[name] = expiry
        elif isinstance(val, str):
            iso = parse_possible_value(val)
            if iso is None:
                continue
            normalized[name] = iso

    if not normalized:
        await update.message.reply_text("No valid VIP entries found.")
        return

    data = load_vip_data()
    data.update(normalized)
    save_vip_data(data)

    await update.message.reply_text(f"✅ Imported {len(normalized)} VIP entries successfully.")

# --- Background task ---
async def check_expired_vips(app):
    while True:
        await asyncio.sleep(86400)  # every 24 hours
        data = load_vip_data()
        now = datetime.utcnow()
        expired = [name for name, exp in data.items() if datetime.fromisoformat(exp) <= now]

        for name in expired:
            try:
                await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ VIP expired for {name}")
            except Exception:
                pass
            del data[name]

        if expired:
            save_vip_data(data)

        if data:
            report_lines = []
            for name, expiry in data.items():
                days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
                report_lines.append(f"{name} — {days_left} days left")

            await app.bot.send_message(chat_id=OWNER_ID, text="📊 Daily VIP Report:\n" + "\n".join(report_lines))

            json_bytes = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
            json_bytes.name = "vip_backup.json"
            await app.bot.send_document(chat_id=OWNER_ID, document=json_bytes, caption="💾 Daily VIP Backup JSON")

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("backup", backup_vip))
    app.add_handler(CommandHandler("importlist", import_vip_list))

    async def on_startup(_app):
        asyncio.create_task(check_expired_vips(_app))

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
