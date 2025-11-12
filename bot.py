import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 8448843919  # your Telegram user ID
VIP_FILE = "vip_data.json"

# === Helpers ===
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

def format_vip_list():
    """Return the VIP list as a readable text message."""
    data = load_vip_data()
    if not data:
        return "No VIPs found."
    lines = []
    for name, expiry_str in data.items():
        try:
            expiry = datetime.fromisoformat(expiry_str)
            days_left = max(0, (expiry - datetime.utcnow()).days)
        except Exception:
            days_left = "unknown"
        lines.append(f"{name} — {days_left} days left")
    return "\n".join(lines)

# === Commands ===
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

async def reduce_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        name = context.args[0]
        days = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reducevip <name> <days>")
        return

    data = load_vip_data()
    if name not in data:
        await update.message.reply_text(f"❌ VIP {name} not found.")
        return

    expiry = datetime.fromisoformat(data[name])
    new_expiry = expiry - timedelta(days=days)
    if new_expiry <= datetime.utcnow():
        del data[name]
        save_vip_data(data)
        await update.message.reply_text(f"⚠️ VIP {name} expired due to reduction.")
    else:
        data[name] = new_expiry.isoformat()
        save_vip_data(data)
        await update.message.reply_text(f"✅ Reduced {name} by {days} days (new expiry: {new_expiry}).")

async def vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    msg = format_vip_list()
    await update.message.reply_text("📊 VIP List:\n" + msg)

async def backup_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual text backup — sends a copy of the list in message format."""
    if update.effective_user.id != OWNER_ID:
        return
    msg = format_vip_list()
    await update.message.reply_text("💾 VIP Backup (message format):\n" + msg)

async def import_vip_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Imports VIPs from text message format."""
    if update.effective_user.id != OWNER_ID:
        return
    text = update.message.text
    lines = text.split("\n")[1:]  # skip the /importlist command line
    data = load_vip_data()

    for line in lines:
        if "—" in line:
            name = line.split("—")[0].strip()
            days_left = line.split("—")[1].split(" ")[0].strip()
            try:
                expiry = datetime.utcnow() + timedelta(days=int(days_left))
                data[name] = expiry.isoformat()
            except:
                continue

    save_vip_data(data)
    await update.message.reply_text(f"✅ Imported {len(lines)} VIPs from message successfully.")

# === Background task ===
async def daily_report(app):
    await asyncio.sleep(5)
    while True:
        await asyncio.sleep(86400)  # every 24 hours
        data = load_vip_data()
        now = datetime.utcnow()

        expired = [n for n, e in data.items() if datetime.fromisoformat(e) <= now]
        for n in expired:
            del data[n]

        if expired or data:
            save_vip_data(data)

        # Notify expired VIPs
        if expired:
            await app.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ Expired VIPs: {', '.join(expired)}")

        # Send daily text backup
        if data:
            report = "📊 Daily VIP Report (message format):\n" + format_vip_list()
            await app.bot.send_message(chat_id=OWNER_ID, text=report)

# === Main ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("reducevip", reduce_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("backup", backup_vip))
    app.add_handler(CommandHandler("importlist", import_vip_list))

    async def on_startup(_app):
        asyncio.create_task(daily_report(_app))
    app.post_init = on_startup

    print("🚀 Starting bot in POLLING mode...")
    app.run_polling(drop_pending_updates=True)
