import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = 8448843919  # your Telegram ID
VIP_FILE = "vip_data.json"

# --- Helpers ---
def load_vip_data():
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

# --- Commands ---
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        name = context.args[0]
        days = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addvip <name> <days>")
        return

    data = load_vip_data()
    expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
    data[name] = expiry
    save_vip_data(data)
    await update.message.reply_text(f"✅ {name} added for {days} days (until {expiry}).")

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    data = load_vip_data()
    if not data:
        await update.message.reply_text("No VIPs found.")
        return

    report = []
    for name, expiry in data.items():
        try:
            days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
        except Exception:
            days_left = "unknown"
        report.append(f"{name} — {days_left} days left")

    await update.message.reply_text("📊 VIP List:\n" + "\n".join(report))

async def backup_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send VIP backup as plain text for copy-paste import."""
    if update.effective_user.id != OWNER_ID:
        return

    data = load_vip_data()
    if not data:
        await update.message.reply_text("No VIP data to back up.")
        return

    lines = [f"{name}|{expiry}" for name, expiry in data.items()]
    backup_text = "\n".join(lines)
    await update.message.reply_text(
        "💾 VIP Backup (copy all lines to import later):\n\n" + backup_text
    )

async def import_vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import VIPs from pasted text or a file."""
    if update.effective_user.id != OWNER_ID:
        return

    text_data = ""
    if update.message.text:
        text_data = update.message.text
    elif update.message.document:
        file = await update.message.document.get_file()
        tmp_path = f"/tmp/{update.message.document.file_name}"
        await file.download_to_drive(tmp_path)
        with open(tmp_path, "r", encoding="utf-8") as f:
            text_data = f.read()
    else:
        await update.message.reply_text("Send VIP data as text or attach a file.")
        return

    lines = text_data.strip().splitlines()
    new_entries = {}
    for line in lines:
        if "|" not in line:
            continue
        name, expiry = line.split("|", 1)
        new_entries[name.strip()] = expiry.strip()

    if not new_entries:
        await update.message.reply_text("No valid VIP entries found.")
        return

    data = load_vip_data()
    data.update(new_entries)
    save_vip_data(data)
    await update.message.reply_text(f"✅ Imported {len(new_entries)} VIP entries successfully.")

# --- Background task ---
async def daily_report(app):
    while True:
        await asyncio.sleep(86400)  # every 24 hours
        data = load_vip_data()
        now = datetime.utcnow()
        expired = [n for n, e in data.items() if datetime.fromisoformat(e) <= now]

        for n in expired:
            del data[n]

        if expired:
            save_vip_data(data)
            await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ Expired VIPs: {', '.join(expired)}")

        if data:
            report = []
            for n, e in data.items():
                days_left = (datetime.fromisoformat(e) - datetime.utcnow()).days
                report.append(f"{n} — {days_left} days left")

            await app.bot.send_message(chat_id=OWNER_ID, text="📊 Daily VIP Report:\n" + "\n".join(report))

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("backup", backup_vip))
    app.add_handler(CommandHandler("importlist", import_vip_list))

    async def on_startup(_app):
        asyncio.create_task(daily_report(_app))

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
