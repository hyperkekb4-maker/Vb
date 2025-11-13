                    text=f"⚠️ VIP expired for user {uid}"
                )
                del data[uid]
            if expired:
                save_vip_data(data)

            # Send daily report as simple text
            if data:
                report_lines = []
                for uid, expiry in data.items():
                    days_left = (datetime.fromisoformat(expiry) - datetime.utcnow()).days
                    report_lines.append(f"ID: {uid} | Days left: {days_left}")

                await app.bot.send_message(
                    chat_id=OWNER_ID,
                    text="📊 Daily VIP Report:\n" + "\n".join(report_lines)
                )

        except Exception as e:
            print(f"Error in VIP checker: {e}")


# --- Main App ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("viplist", vip_list))
    app.add_handler(CommandHandler("exportvip", export_vip))
    app.add_handler(CommandHandler("importvip", import_vip))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Background VIP checker
    async def on_startup(app_instance):
        asyncio.create_task(check_expired_vips(app_instance))

    app.post_init = on_startup

    print("🚀 Starting bot in WEBHOOK mode...")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
