import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram.ext import ApplicationBuilder

# ---------------- Dummy HTTP Server for Render ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), Handler)
    print(f"🌐 HTTP server listening on port {port} (for Render port detection)")
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# ---------------- Main Bot ----------------
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

    # Background task (run after bot starts)
    application.create_task(vip_checker(application))

    print("🤖 Bot started in POLLING mode...")
    await application.run_polling()  # PTB handles the event loop

if __name__ == "__main__":
    asyncio.run(main())
