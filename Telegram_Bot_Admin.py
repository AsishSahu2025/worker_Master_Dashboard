# import logging
# from telegram.ext import Updater, CommandHandler, PollAnswerHandler, PollHandler, MessageHandler, Filters, CallbackContext
# from telegram import Bot, Update, error
# from typing import Optional, Dict, Any
# import telegram
# import time 

# class CustomRequest(telegram.utils.request.Request):
#     def __init__(
#         self,
#         con_pool_size: int = 50,
#         proxy_url: Optional[str] = None,
#         urllib3_proxy_kwargs: Optional[Dict[str, Any]] = None,
#         connect_timeout: Optional[float] = None,
#         read_timeout: Optional[float] = None,
#     ):
#         super().__init__(
#             con_pool_size=con_pool_size,
#             proxy_url=proxy_url,
#             urllib3_proxy_kwargs=urllib3_proxy_kwargs,
#             connect_timeout=connect_timeout,
#             read_timeout=read_timeout,
#         )

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Telegram bot token and group ID
# TOKEN = '7146036921:AAFL-Llw1YlKHJNHkAuVNuWxHKE88h0oE0s'
# GROUP_ID = '-4228110606'

# bot = Bot(token=TOKEN, request=CustomRequest(con_pool_size=50))
# updater = Updater(bot=bot, use_context=True)

# def send_message(args):
#     try:
#         if args == False:
#             time.sleep(1)
#             bot.send_message(chat_id=GROUP_ID, text="Dear Admin,\n\nThere is a Power failure from Magnum Fisheries.")
#     except error.TelegramError as e:
#         logger.error(f"Error sending poll: {e}")

# send_message(False)