from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, PollAnswerHandler, PollHandler, MessageHandler, Filters, CallbackContext
import time, logging
from django.core.cache import cache

TOKEN = '6995943945:AAEYlcaF5CTYZMSvyQ7cvCn9vbIxJic0y90'
GROUP_ID = '-1002041247290'
bot = Bot(token=TOKEN)


import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def send_reminder_on_unanswered_poll(chat_id, poll_id):
    print(poll_id)
    try:
        # Send a reminder message to the chat about the unanswered poll
        message_text = "Reminder: The poll has not received responses yet. Please respond."
        bot.send_message(chat_id=chat_id, text=message_text, reply_to_message_id=poll_id)
        logger.info("Reminder message sent successfully.")
    except Exception as e:
        logger.error(f"Error sending reminder message: {e}")

# Example usage:
send_reminder_on_unanswered_poll(GROUP_ID, 472)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
