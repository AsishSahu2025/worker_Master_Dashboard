
# from django.db import transaction
# import time
# import threading
# from datetime import datetime, timedelta
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.cron import CronTrigger
# from apscheduler.triggers.interval import IntervalTrigger
# from apscheduler.triggers.date import DateTrigger

# import redis
# import logging
# import pytz
# import psycopg2
# from django.conf import settings
# from django.core.management.base import BaseCommand
# from telegram import Bot, Update
# from telegram.ext import Updater, CommandHandler, PollAnswerHandler, MessageHandler, Filters, CallbackContext, PollHandler
# import signal
# import sys

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Telegram bot token and group ID
# TOKEN = '8161327153:AAHPXDNAYlhH893fu1jfG2uhIHXji3-cMr0'

# YOUR_REDIS_HOST = settings.REDIS_HOST
# YOUR_REDIS_PASSWORD = settings.REDIS_PASSWORD
# YOUR_REDIS_PORT = settings.REDIS_PORT
# # YOUR_REDIS_DB = settings.REDIS_DB

# DATABASE_CONFIG = {
#     'host': settings.DATABASES['default']['HOST'],
#     'database': settings.DATABASES['default']['NAME'],
#     'user': settings.DATABASES['default']['USER'],
#     'password': settings.DATABASES['default']['PASSWORD'],
# }

# # Create bot instance
# bot = Bot(token=TOKEN)

# class Command(BaseCommand):
#     help = 'Run the Telegram bot'

#     def __init__(self) -> None:
#         super().__init__()
#         self.r = None
#         self.connect_redis()
#         # self.scheduler = BackgroundScheduler()  # Initialize APScheduler
#         self.start_data_finding_thread()
#         self.start_daily_schedule_thread()
#         self.start_task_reminder_thread()
       
        
#     def connect_redis(self):
#         try:
#             self.r = redis.Redis(host=YOUR_REDIS_HOST, port=YOUR_REDIS_PORT,db=0, password=YOUR_REDIS_PASSWORD, ssl=True )
#             # self.r = redis.Redis(host=YOUR_REDIS_HOST, port=YOUR_REDIS_PORT, db=YOUR_REDIS_DB, password=YOUR_REDIS_PASSWORD, ssl=True)
#             # self.r = redis.Redis(host='localhost', port=6379, db=0)
#             # self.r.flushdb()
#             self.r.ping()
#             logger.info("Connected to Redis")
#         except redis.ConnectionError as e:
#             logger.error(f"Redis connection error: {e}")
#             raise e

#     def start_data_finding_thread(self):
#         thread = threading.Thread(target=self.find_the_data, daemon=True)
#         thread.start()
        
#     def start_daily_schedule_thread(self):
#         """Start the thread for daily task scheduling."""
#         thread = threading.Thread(target=self.daily_schedule, daemon=True)
#         thread.start()

#     def start_task_reminder_thread(self):
#         """Start the thread to handle task reminders."""
#         thread = threading.Thread(target=self.task_reminder_scheduler, daemon=True)
#         thread.start()
        

#     def handle(self, *args, **options):
#         logger.info("Starting bot...")
#         updater = Updater(token=TOKEN, use_context=True)
#         dispatcher = updater.dispatcher
#         dispatcher.add_handler(MessageHandler(Filters.photo, self.photo_received))
#         dispatcher.add_handler(MessageHandler(Filters.location, self.location_received))
#         dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.photo_type_received))


#         # Start polling for updates
#         updater.start_polling()
#         logger.info("Bot polling started.")

#     def photo_received(self, update: Update, context: CallbackContext):
#         user_id = update.effective_user.id
#         photo = update.message.photo[-1]  # Get highest resolution photo
#         file_id = photo.file_id
        
#         self.r.set(f"user:{user_id}:photo_file_id", file_id)
#         self.r.set(f"user:{user_id}:state", "awaiting_location")

#         update.message.reply_text("Please share your location before proceeding.")

#     def location_received(self, update: Update, context: CallbackContext):
#         user_id = update.effective_user.id
#         state = self.r.get(f"user:{user_id}:state")

#         if state and state.decode() == "awaiting_location":
#             lat = update.message.location.latitude
#             lon = update.message.location.longitude
#             self.r.set(f"user:{user_id}:latitude", lat)
#             self.r.set(f"user:{user_id}:longitude", lon)
#             self.r.set(f"user:{user_id}:state", "awaiting_type")

#             update.message.reply_text(
#                 "Please select the photo type:\n1. Truck\n2. Received Chalan\n3. Chalan\n4. Shrimp Boxes"
#             )
#         else:
#             update.message.reply_text("Please send a photo first.")

#     def photo_type_received(self, update: Update, context: CallbackContext):
#         user_id = update.effective_user.id
#         state = self.r.get(f"user:{user_id}:state")

#         if not state or state.decode() != "awaiting_type":
#             return

#         text = update.message.text.strip().lower()
#         type_map = {
#             "1": "truck",
#             "truck": "truck",
#             "2": "received_chalan",
#             "received chalan": "received_chalan",
#             "3": "chalan",
#             "4": "shrimp_boxes",
#             "shrimp boxes": "shrimp_boxes",
#         }

#         photo_type = type_map.get(text)
#         if not photo_type:
#             update.message.reply_text("Invalid type. Please reply with one of the 4 options.")
#             return

#         # Retrieve info
#         file_id = self.r.get(f"user:{user_id}:photo_file_id").decode()
#         lat = float(self.r.get(f"user:{user_id}:latitude").decode())
#         lon = float(self.r.get(f"user:{user_id}:longitude").decode())

#         # Save to DB
#         from your_app.models import PhotoSubmission
#         submission = PhotoSubmission.objects.create(
#             user_id=user_id,
#             photo_file_id=file_id,
#             latitude=lat,
#             longitude=lon,
#             photo_type=photo_type
#         )

#         update.message.reply_text("Photo saved successfully. Thank you!")

#         # Cleanup
#         self.r.delete(f"user:{user_id}:photo_file_id")
#         self.r.delete(f"user:{user_id}:latitude")
#         self.r.delete(f"user:{user_id}:longitude")
#         self.r.delete(f"user:{user_id}:state")
