from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes

# Replace these
BOT_TOKEN = "8440911849:AAHzeMIWuZYOR_EUxXPZ8eX0WVbYQfJauFM"
ADMIN_ID = "HXDM100"
WALLET_USDT_TRC20 = "TSxvZs96scypQ2Bc67c4jqN68fdNVCJNKw"
WALLET_USDT_BNB = "0xa8F380Ef9BC7669418B9a8e4bA38EA2d252d0003"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Buy VIP", callback_data="buy_vip")]
    ]
    await update.message.reply_text(
        "Welcome! 👋\nChoose an option below:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy_vip":
        keyboard = [
            [InlineKeyboardButton("USDT TRC20", callback_data="pay_trc20")],
            [InlineKeyboardButton("USDT BNB", callback_data="pay_bnb")],
        ]
        await query.edit_message_text(
            "Select your payment option:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "pay_trc20":
        text = (
            "💳 After depositing to Wallet, send the screenshot below.\n"
            "Usually confirmed in less than 30 minutes.\n\n"
            "💰 USDT TRC20 Wallet:\n"
            f"{WALLET_USDT_TRC20}\n\n"
            "💎 VIP Access: $300 - Lifetime\n"
            "\nPress the button below to send your receipt."
        )
        keyboard = [[InlineKeyboardButton("Send Receipt", callback_data="send_receipt")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "pay_bnb":
        text = (
            "💳 After depositing to Wallet, send the screenshot below.\n"
            "Usually confirmed in less than 30 minutes.\n\n"
            "💰 USDT BNB (BEP20) Wallet:\n"
            f"{WALLET_USDT_BNB}\n\n"
            "💎 VIP Access: $300 - Lifetime\n"
            "\nPress the button below to send your receipt."
        )
        keyboard = [[InlineKeyboardButton("Send Receipt", callback_data="send_receipt")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "send_receipt":
        await query.edit_message_text(
            "📸 Please send the screenshot of your payment in this chat."
        )
