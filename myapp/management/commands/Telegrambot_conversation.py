import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from django.core.management.base import BaseCommand
# from telegram_bot.bot import run_bot
 
 
class Command(BaseCommand):
    help = "Starts the Telegram bot"
 
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Telegram bot...")
        #run_bot()
        import asyncio
        asyncio.run(run_bot())
 
# Logger setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Scheduler setup
#scheduler = AsyncIOScheduler(timezone=timezone("UTC"))
 
# Constants 
# TOKEN = "8161327153:AAHPXDNAYlhH893fu1jfG2uhIHXji3-cMr0"  
# ADMIN_USER_ID = 1106883275  

TOKEN = "8359846344:AAG_LPrbj0weS27hUeUF8Fi1Zxcl9W-kFSU"  
ADMIN_USER_ID = 5016162677
 
# Global storage for user data
user_data = {
    # "@Rpajesh": {"username": "@Rpajesh"},
    # "@Tapaskumar1996": {"username": "@Tapaskumar1996"},
    # "@soumya3234": {"username": "@soumya3234"},
    # "@Rajeswarironita943": {"username": "@Rajeswarironita943"},
}
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and stores group users' chat IDs automatically."""
    user = update.message.from_user
    chat_id = update.message.chat_id
    username = user.username if user.username else f"{user.first_name}_{user.id}"
 
    user_data[username] = {}
    context.user_data["chat_id"] = chat_id
 
    if username not in user_data:
        user_data[username] = {"chat_id": chat_id, "messages": []}
 
    keyboard = [
        [InlineKeyboardButton("#power_failure", callback_data="power_failure")],
        [InlineKeyboardButton("#aerator_fail", callback_data="aerator_fail")],
        [InlineKeyboardButton("#short_circuit", callback_data="short_circuit")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
 
    await update.message.reply_text(f"Welcome {user.first_name}! Select an issue:", reply_markup=reply_markup)
 
 
async def handle_predefined_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles predefined messages from button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data
 
    messages = {
                "power_failure": "⚠️ Attention: Power is failed. Change over to DG immediately.",
                "aerator_fail": "🌊 Alert: Aerator No. 5 has failed. Turn it on manually.",
                "short_circuit": "🚨 Warning: Short circuit detected in Pond 1. Turn off the main switch immediately."
            }
 
 
    if data in messages:
        message_text = messages[data]
 
        if query.from_user.id == ADMIN_USER_ID:
            context.user_data["selected_message"] = message_text
 
            all_users = list(user_data.keys())
            keyboard = [
                [InlineKeyboardButton(f"Send to {username}", callback_data=f"send_{username}")]
                for username in all_users
            ]
 
            if not keyboard:
                keyboard.append([InlineKeyboardButton("No users available", callback_data="no_users")])
 
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("👥 Select a user to send the message to:", reply_markup=reply_markup)
        else:
            await query.answer("❌ Access Denied.", show_alert=True)
            return
 
 
async def send_predefined_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message only if the admin clicks the option."""
    query = update.callback_query
    user_id = query.from_user.id
 
    if user_id != ADMIN_USER_ID:
        await query.answer(text="❌ You are not authorized to send messages.", show_alert=True)
        return
 
    await query.answer()
 
    data = query.data
    if not data.startswith("send_"):
        return
 
    username = data.split("send_", 1)[1]
 
    if username not in user_data:
        await query.message.reply_text("❌ User not found.")
        return
 
    if "selected_message" not in context.user_data:
        await query.message.reply_text("⚠️ No message selected. Please choose a predefined message first.")
        return
 
    message_text = context.user_data["selected_message"]
    user_chat_id = context.user_data.get("chat_id")
    if not user_chat_id:
        await query.message.reply_text("⚠️ Cannot send message, chat ID missing.")  
        return
 
    await context.bot.send_message(chat_id=user_chat_id, text=f"📩 Message from Admin to {username}: {message_text}")
 
 
 
 
 
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Automatically store all users who send messages."""
    user = update.message.from_user
    username = user.username or f"User_{user.id}"
 
    if username not in user_data:
        user_data[username] = {"chat_id": update.message.chat_id, "messages": []}
 
    user_data[username]["messages"].append(update.message.text)
    await update.message.reply_text("✅ Message received! An admin will respond soon.")
 
 
def run_bot() -> None:
    """Starts the Telegram bot."""        
    application = ApplicationBuilder().token(TOKEN).build()
 
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_USER_ID), handle_message))
    application.add_handler(CallbackQueryHandler(handle_predefined_options, pattern="^(power_failure|short_circuit|aerator_fail)$"))
    application.add_handler(CallbackQueryHandler(send_predefined_message, pattern="^send_"))
 
    print("🚀 Telegram bot is running...")
    application.run_polling()
 