
from django.db import transaction
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

import redis
import logging
import pytz
import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, PollAnswerHandler, MessageHandler, Filters, CallbackContext, PollHandler
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token and group ID
TOKEN = '7822480011:AAELVUcySA8phvfHaj6G63QAhG_M8IoPM7g'

YOUR_REDIS_HOST = settings.REDIS_HOST
YOUR_REDIS_PASSWORD = settings.REDIS_PASSWORD
YOUR_REDIS_PORT = settings.REDIS_PORT
# YOUR_REDIS_DB = settings.REDIS_DB

DATABASE_CONFIG = {
    'host': settings.DATABASES['default']['HOST'],
    'database': settings.DATABASES['default']['NAME'],
    'user': settings.DATABASES['default']['USER'],
    'password': settings.DATABASES['default']['PASSWORD'],
}

# Create bot instance
bot = Bot(token=TOKEN)

class Command(BaseCommand):
    help = 'Run the Telegram bot'

    def __init__(self) -> None:
        super().__init__()
        self.r = None
        self.connect_redis()
        # self.scheduler = BackgroundScheduler()  # Initialize APScheduler
        self.start_data_finding_thread()
        self.start_daily_schedule_thread()
        self.start_task_reminder_thread()
       
        
    def connect_redis(self):
        try:
            self.r = redis.Redis(host=YOUR_REDIS_HOST, port=YOUR_REDIS_PORT,db=0, password=YOUR_REDIS_PASSWORD, ssl=True )
            # self.r = redis.Redis(host=YOUR_REDIS_HOST, port=YOUR_REDIS_PORT, db=YOUR_REDIS_DB, password=YOUR_REDIS_PASSWORD, ssl=True)
            # self.r = redis.Redis(host='localhost', port=6379, db=0)
            # self.r.flushdb()
            self.r.ping()
            logger.info("Connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise e

    def start_data_finding_thread(self):
        thread = threading.Thread(target=self.find_the_data, daemon=True)
        thread.start()
        
    def start_daily_schedule_thread(self):
        """Start the thread for daily task scheduling."""
        thread = threading.Thread(target=self.daily_schedule, daemon=True)
        thread.start()

    def start_task_reminder_thread(self):
        """Start the thread to handle task reminders."""
        thread = threading.Thread(target=self.task_reminder_scheduler, daemon=True)
        thread.start()
        

    def handle(self, *args, **options):
        logger.info("Starting bot...")
        updater = Updater(token=TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        # Register handlers
        dispatcher.add_handler(PollAnswerHandler(self.poll_response))
        # dispatcher.add_handler(PollHandler(self.shrimp_size_poll_response))
        dispatcher.add_handler(MessageHandler(Filters.location, self.ask_location))

        # Start polling for updates
        updater.start_polling()
        logger.info("Bot polling started.")


    def fetch_tasks_for_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = []

        task_keys = self.r.keys(f"task:*")
        for key in task_keys:
            task_data = self.r.hgetall(key)
            task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}
            logger.info(f"Key: {key}, Date: {task_data.get('date')}")
            if task_data.get('date') == today:
                tasks.append(task_data)

        if not tasks:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute("""SELECT * FROM tasks WHERE date = %s""", [today])
            rows = cur.fetchall()
            for row in rows:
                
                tasks.append({
                    'category_name': row[1],
                    'date': row[2],
                    'from_time': row[3],
                    'to_time': row[4],
                    'worker_name': row[5],
                    'group_id': row[6],
                    'task_id': row[7],
                    'pond_id': row[8]
                })
                
            conn.close()
 
        return tasks

    def send_daily_task_summary(self):
        tasks = self.fetch_tasks_for_today()
        if tasks:
            task_summary_message = "Good morning! Here are your tasks for today:\n\n"
            for task in tasks:
                task_summary_message += f"Task: {task['category_name']}\n"
                task_summary_message += f"Worker: {task['worker_name']}\n"
                task_summary_message += f"pond_id: {task['pond_id']}\n"
                task_summary_message += f"Time: {task['from_time']} - {task['to_time']}\n\n"

            group_id = tasks[0]['group_id']  # You can send it to the group of the first task or handle multiple groups.
            logger.info(f"Sending to group_id: {group_id}")
            bot.send_message(chat_id=group_id, text=task_summary_message)
            logger.info(f"Sent task summary to group {group_id}")
        else:
            logger.info("No tasks found for today.")

    def daily_schedule(self):
        """Schedule the daily task summary at 6 AM every day"""
        while True:
            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
            current_hour = now.hour
            current_minute = now.minute

            # Send daily task summary at 6 AM
            if current_hour == 7 and current_minute == 0:
                try:
                    self.send_daily_task_summary()
                    logger.info("Sent daily task summary at 6 AM.")
                except Exception as e:
                    logger.error(f"Error sending daily task summary: {e}")
                
                # Sleep for a minute to prevent it from triggering multiple times within the same minute
                time.sleep(60)

            else:
                time.sleep(60)  # Check again after 1 minute

    def send_task_reminder(self, task):
        """Send reminder for the task 10 minutes before the start time"""
        group_id = task['group_id']
        task_reminder_message = f"Reminder: Your task '{task['category_name']}' for '{task['pond_id']}' starts in 10 minutes!"
        logger.info(f"Sending reminder to Group ID: {group_id}")
        bot.send_message(chat_id=group_id, text=task_reminder_message)
        logger.info(f"Sent reminder for task {task['category_name']} to group {group_id}")

    def task_reminder_scheduler(self):
        """Schedule task reminders 10 minutes before the task starts"""
        sent_reminders = set()  # Keep track of tasks for which reminders have already been sent

        while True:
            tasks = self.fetch_tasks_for_today()
            timezone = pytz.timezone("Asia/Kolkata")  # Ensure timezone is correctly set for all times

            for task in tasks:
                task_id = task['task_id']  # Assuming task has a unique ID
                print(task_id )
                if task_id in sent_reminders:
                    continue  # Skip if the reminder has already been sent for this task

                from_time_str = task['from_time']
                from_time = datetime.strptime(from_time_str, "%H:%M")  # Parse the task start time
                today = datetime.now(timezone).date()  # Get today's date in the specified timezone
                from_time = datetime.combine(today, from_time.time())  # Combine date with start time
                
                # Calculate the reminder time (10 minutes before the task start)
                reminder_time = from_time - timedelta(minutes=10)  # Subtract 10 minutes instead of 13
                
                # Make both reminder_time and current_time timezone-aware
                reminder_time = timezone.localize(reminder_time)  # Localize reminder_time to Asia/Kolkata
                current_time = datetime.now(timezone)  # Make current_time timezone-aware
                print(reminder_time, current_time)
                logger.info(f"Checking task {task_id}: reminder at {reminder_time}, current time {current_time}")

                # If it's time (or slightly past), send reminder
                if current_time > reminder_time:
                    continue

                # Check periodically until the reminder time is reached
                while current_time < reminder_time:
                    # Sleep and check periodically until the reminder time is reached
                    time.sleep(5)  # Sleep for 5 seconds to reduce frequent checks
                    current_time = datetime.now(timezone)  
                # Once the reminder time is reached, send the reminder
                self.send_task_reminder(task)
                sent_reminders.add(task_id)  # Mark this task's reminder as sent
            
            # Sleep for a while before checking tasks again (could be adjusted)
            time.sleep(60)  # Check tasks again after a minute



    def poll_response(self, update, context):
        try:
            poll_answer = update.poll_answer
            if not poll_answer:
                logger.error("Poll answer is None.")
                return

            poll_id = poll_answer.poll_id
            logger.info(f"Poll ID: {poll_id}")

            # Retrieve all task data from Redis
            # This will include both the time_poll_id and size_poll_id.
            task_keys = self.r.keys("task_status:*")  # Retrieve all task keys stored under "task_status:"

            matched_task = None
            for task_key in task_keys:
                task_data = self.r.hgetall(task_key)  # Get task data for each task
                task_data_dict = {key.decode('utf-8'): value.decode('utf-8') for key, value in task_data.items()}

                # Check if the poll_id matches the time_poll_id or size_poll_id in the task data
                stored_time_poll_id = task_data_dict.get("time_poll_id")
                stored_size_poll_id = task_data_dict.get("size_poll_id")
                stored_color_poll_id = task_data_dict.get("color_poll_id")
                stored_dieses_poll_id = task_data_dict.get("dieses_poll_id")
                stored_moulting_poll_id = task_data_dict.get("moulting_poll_id")

                # If poll_id matches time_poll_id or size_poll_id, we have found the task
                if poll_id == stored_time_poll_id or poll_id == stored_size_poll_id or poll_id == stored_color_poll_id or poll_id == stored_dieses_poll_id or poll_id == stored_moulting_poll_id:
                    matched_task = task_data_dict
                    break  # Exit the loop once we have found the matching task

            if matched_task:
                logger.info(f"Task matched: {matched_task}")

                # Now that we have the matched task, handle the response accordingly
                if poll_id == matched_task.get("time_poll_id"):
                    logger.info(f"Handling response for the time poll (Poll ID: {poll_id})")
                    self.handle_first_poll_response(update, context)

                elif poll_id == matched_task.get("size_poll_id"):
                    logger.info(f"Handling response for the shrimp size poll (Poll ID: {poll_id})")
                    self.shrimp_size_poll_response(update, context)
                    
                elif poll_id == matched_task.get("color_poll_id"):
                    logger.info(f"Handling response for the shrimp color poll (Poll ID: {poll_id})")
                    self.shrimp_color_poll_response(update, context)
                    
                elif poll_id == matched_task.get("dieses_poll_id"):
                    logger.info(f"Handling response for the shrimp dieses poll (Poll ID: {poll_id})")
                    self.shrimp_dieses_poll_response(update, context)
                    
                elif poll_id == matched_task.get("moulting_poll_id"):
                    logger.info(f"Handling response for the shrimp moulting poll (Poll ID: {poll_id})")
                    self.shrimp_moulting_poll_response(update, context)

            else:
                logger.warning(f"Received response for an unknown poll: {poll_id}")

        except Exception as e:
            logger.error(f"Error processing poll response: {e}")



    def send_poll(self, **kwargs):
        try:
            
            # Send the poll
            message = bot.send_poll(
                chat_id=kwargs['group_id'],
                question=f"{kwargs['worker_name']}, Task for you.\n\nTask Name:\n{kwargs['task_name']}.\n\nTime Duration:\n{kwargs['from_time']}-{kwargs['to_time']}",
                options=kwargs['options'],
                is_anonymous=False,
                allows_multiple_answers=False,
            )
            
            # Prepare the raw SQL queries
            pond_id = kwargs['pond_id']
            task_id = kwargs['task_id']
            task_name = kwargs['task_name']
            date = kwargs['date']
            worker_name = kwargs['worker_name']
            message_id = message.message_id
            time_poll_id = message.poll.id
            group_id = kwargs['group_id']
            print(group_id)
            
            # Set the group id and poll id in Redis 
            time_poll_redis_key = f"time_poll:{time_poll_id}"  # Using time_poll_id for the main poll
            self.r.hset(time_poll_redis_key, "group_id", group_id)
            self.r.expire(time_poll_redis_key, 86400)
            print(group_id)
            # Insert into Task_status table using raw SQL
            conn = psycopg2.connect(**DATABASE_CONFIG)
            print("connected")
            cur = conn.cursor() 
            cur.execute("""
                INSERT INTO myapp_task_status (name, time, date, latitude, longitude, status, username, pond_id_id, task_id_id, message_id, time_poll_id, shrimp_size,shrimp_color, diesese, moulting, size_poll_id,color_poll_id,dieses_poll_id,moulting_poll_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                task_name, '', date, '', '', '', worker_name, pond_id, task_id, message_id, time_poll_id,  '', '', '', '', None, None, None, None
            ])
            conn.commit()
            conn.close()

            # Create task_status dictionary
            task_status = {
                'name': task_name,
                'time': "",
                'date': date,
                'latitude': "",
                'longitude': "",
                'status': "",
                'username': worker_name,
                'pond_id': pond_id,
                'task_id': task_id,
                'message_id': message_id,
                'time_poll_id': time_poll_id,
                'shrimp_size': "",
                'shrimp_color': "",
                'diesese': "",
                'moulting': "",
                "size_poll_id": "",
                "color_poll_id": "",
                "dieses_poll_id": "",
                "moulting_poll_id": "",
            }
            task_data = {key: str(value) for key, value in task_status.items()}
            send_poll_redis_key = f"task_status:{time_poll_id}" 
            self.r.hset(send_poll_redis_key, mapping=task_data)
            self.r.expire(send_poll_redis_key, 86400)

        except Exception as e:
            logger.error(f"Error sending poll: {e}")
            raise

    def handle_first_poll_response(self, update: Update, context: CallbackContext):
        logger.info(f"Received update: {update}")  # Log the entire update object for debugging
        poll_answer = update.poll_answer

        if poll_answer is not None:
            time_poll_id = poll_answer.poll_id  # Get the time_poll_id from the poll answer
            logger.info(f"Time Poll ID: {time_poll_id} - Processing poll response.")

            # Check if the time_poll_id matches with the saved time_poll_id
            task_status_key = f"task_status:{time_poll_id}"  # Use time_poll_id here
            print(task_status_key) 
            task_status = self.r.hgetall(task_status_key)
            print(task_status)

            if not task_status:
                logger.error(f"Task status not found in Redis for time_poll_id {time_poll_id}")
                return

            option_ids = poll_answer.option_ids  # Get the selected option IDs
            if not option_ids:
                logger.error("No options selected in the poll.")
                return

            options = ['Yes', 'No']
            selected_options = [options[i] for i in option_ids]  # Get the selected option texts
            logger.info(f"Selected options: {selected_options}")

            # If "Yes" is selected, set the status to "Yes", otherwise "No"
            status = 'Yes' if 'Yes' in selected_options else 'No'

            # Update the task_status in Redis
            task_status['status'] = status
            task_status['time'] = datetime.now().strftime("%H:%M")
            self.r.hmset(task_status_key, task_status)

            # Update the database with the new status (using time_poll_id instead of poll_id)
            try:
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                cur.execute("""
                    UPDATE myapp_task_status
                    SET status = %s, time = %s
                    WHERE time_poll_id = %s  
                """, [status, task_status['time'], time_poll_id])  # Use time_poll_id here
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error updating database: {e}")

            # Send message based on response
            extracting_group_id = self.r.hget(f"time_poll:{time_poll_id}", "group_id")  # Fetch using the correct key
            print("Extracted group_id:", extracting_group_id)
            if extracting_group_id:
                extracted_group_id = int(extracting_group_id.decode("utf-8"))
                logger.info(f"Extracted group_id: {extracted_group_id}")

                # Store group_id in task_status for future use in subsequent polls
                task_status['group_id'] = extracted_group_id
                self.r.hmset(task_status_key, task_status)

            # If "Yes" was selected, prompt for location
            if status == "Yes":
                time.sleep(1)
                bot.send_message(chat_id=extracted_group_id, text="Please share your location.")
            else:
                bot.send_message(chat_id=extracted_group_id, text="Task declined. Let us know if anything changes.")

                
    @transaction.atomic
    def ask_location(self, update: Update, context: CallbackContext):
        username = update.message.from_user.username
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude

        chat_id = update.effective_chat.id
        try:
            task_keys = self.r.keys("task_status:*")
            sorted_task_keys = sorted(task_keys)

            for key in reversed(sorted_task_keys):
                task_data = self.r.hgetall(key)
                print(task_data,"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
                task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

                if task_data.get('status') == 'Yes' and task_data.get('username') == username:
                    self.r.hset(key, mapping={'latitude': latitude, 'longitude': longitude})
                    break
                else:
                    continue
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute(""" 
                SELECT id , name FROM myapp_task_status
                WHERE username = %s
                ORDER BY id DESC
                LIMIT 1
            """, [username])
            result = cur.fetchone()

            if result and len(result) >= 2:
                task_status_id = result[0]
                name = result[1]  # Fetch the task name from the result

                cur.execute(""" 
                    UPDATE myapp_task_status
                    SET latitude = %s, longitude = %s
                    WHERE id = %s
                """, [latitude, longitude, task_status_id])
                conn.commit()
                bot.send_message(chat_id=update.effective_chat.id, text=f"{username}, Location saved successfully. Let's proceed with the shrimp size poll.")

                # Now trigger the shrimp size poll
                print("________________________________________________________________")
                if name == "Feed Tray":
                    print(name,"++++++++++++++++++++++")
                    # Trigger shrimp size poll only if the task name is "Feed Tray"
                    # and the status is "Yes"
                    task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in self.r.hgetall(key).items()}
                    print(task_data,"-------------------------------------------------")
                    self.send_shrimp_size_poll(update, task_data, key)
            else:
                logger.error(f"Task_status for {username} does not exist.")
                bot.send_message(chat_id=update.effective_chat.id, text="Error: Task_status not found.")

                conn.close()

        except Exception as e:
            logger.error(f"Error updating location: {e}")
            bot.send_message(chat_id=update.effective_chat.id, text="An error occurred while saving the location. Please try again.")

    def send_shrimp_size_poll(self, update, task_data, task_key):
        try:
            group_id = task_data.get('group_id')
            if not group_id:
                logger.error(f"Error: group_id is not available for task_key {task_key}.")
                return
            # Send the shrimp size poll
            shrimp_size_poll = bot.send_poll(
                chat_id=update.effective_chat.id,  # Using the chat_id from the update
                question="Please select the shrimp size.",  # Question text
                options=["Small", "Medium", "Large"],  # Shrimp size options
                is_anonymous=False,
                allows_multiple_answers=False
            )

            # Get the size_poll_id from the sent poll
            size_poll_id = shrimp_size_poll.poll.id
            logger.info(f"Sent shrimp size poll with size_poll_id: {size_poll_id}")  # Log the size_poll_id for debugging

            # Fetch the existing task data from Redis using the task_key
            existing_task_data = self.r.hgetall(task_key)

            # If no data is found, log an error and return
            if not existing_task_data:
                logger.error(f"No task data found for task_key {task_key}.")
                return

            # Convert bytes to string for easier handling
            existing_task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in existing_task_data.items()}

            # Update the task data with the new size_poll_id
            existing_task_data['size_poll_id'] = str(size_poll_id)
            # group_id = existing_task_data.get('group_id')

            # # Check if group_id exists in task_data
            # if not group_id:
            #     logger.error(f"Error: group_id is not available for task_key {task_key}.")
            #     return

            logger.info(f"Captured group_id: {group_id}")


            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=existing_task_data)
            self.r.expire(task_key, 86400)  # Expire after 24 hours

            # Log the updated task data for debugging purposes
            logger.info(f"Updated task data in Redis with size_poll_id: {existing_task_data}")

            # Update the database with the new size_poll_id
            task_id = existing_task_data.get('task_id')
            if task_id:
                try:
                    conn = psycopg2.connect(**DATABASE_CONFIG)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE myapp_task_status
                        SET size_poll_id = %s
                        WHERE task_id_id = %s
                    """, [size_poll_id, task_id])  # Update the database task record with size_poll_id
                    conn.commit()
                    conn.close()
                    logger.info(f"Successfully saved shrimp size poll ID {size_poll_id} to database.")
                except Exception as e:
                    logger.error(f"Error updating database with size_poll_id: {e}")
                    raise
            else:
                logger.error(f"Task ID not found in the existing task data for task_key {task_key}.")

        except Exception as e:
            logger.error(f"Error sending shrimp size poll: {e}")
            raise


            
    def shrimp_size_poll_response(self, update: Update, context: CallbackContext):
        try:
            # Log the received update for debugging
            logger.info(f"Received update: {update}")  
            
            # Extract poll answer details
            poll_answer = update.poll_answer
            size_poll_id = poll_answer.poll_id  # Get the poll ID
            selected_option = poll_answer.option_ids  # Get the selected option(s) (list of indices)

            # Shrimp size options
            shrimp_size_options = ["Small", "Medium", "Large"]
            selected_size = [shrimp_size_options[i] for i in selected_option]

            # Log the selected shrimp size(s)
            logger.info(f"Received response for poll_id: {size_poll_id} - Selected shrimp size(s): {selected_size}")

            # Fetch all task keys in Redis and iterate over them
            task_keys = self.r.keys("task_status:*")  # Fetch all task keys in Redis
            matched_task = None

            for task_key in task_keys:
                # Get the task data for the current task_key
                task_data = self.r.hgetall(task_key)

                if not task_data:
                    continue

                # Convert task data to a dictionary (from bytes to strings)
                task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

                # Check if the current task has the matching size_poll_id
                if task_data.get('size_poll_id') == size_poll_id:
                    matched_task = task_data
                    break

            if not matched_task:
                logger.error(f"No task found for size_poll_id {size_poll_id}.")
                return

            # Extract the task_id from the matched task
            task_id = matched_task.get('task_id')
            group_id = matched_task.get('group_id')
            
            if not task_id:
                logger.error(f"Task ID not found in matched task data for size_poll_id {size_poll_id}.")
                return

            logger.info(f"Task ID for size_poll_id {size_poll_id}: {task_id}")

            # Update the shrimp_size in the matched task data
            matched_task['shrimp_size'] = ", ".join(selected_size)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=matched_task)
            self.r.expire(task_key, 86400)  # Expire in 24 hours
            
            # Log the updated task data in Redis for debugging
            logger.info(f"Updated task data in Redis with shrimp_size: {matched_task}")

            # Update the shrimp_size in the database
            try:
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                # Update the database task record with the shrimp_size
                cur.execute("""
                    UPDATE myapp_task_status
                    SET shrimp_size = %s
                    WHERE task_id_id = %s
                """, [", ".join(selected_size), task_id])  # Update with selected shrimp size
                conn.commit()
                conn.close()
                # Log successful database update
                logger.info(f"Successfully saved shrimp size response to database for task_id {task_id}.")
                self.send_shrimp_color_poll(group_id, matched_task, task_key)
                

            except Exception as e:
                logger.error(f"Error updating database with shrimp size response: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error processing poll answer: {e}")
            raise









    def send_shrimp_color_poll(self, group_id, task_data, task_key):
        try:
            # Send the shrimp color poll
            shrimp_color_poll = bot.send_poll(
                chat_id=group_id,  # Using the provided chat_id
                question="Please select the shrimp color.",
                options=["Red", "Green", "Blue", "Yellow"],
                is_anonymous=False,
                allows_multiple_answers=False
            )

            # Get the color_poll_id from the sent poll
            color_poll_id = shrimp_color_poll.poll.id
            logger.info(f"Sent shrimp color poll with color_poll_id: {color_poll_id}")

            # Fetch the existing task data from Redis using the task_key
            existing_task_data = self.r.hgetall(task_key)

            if not existing_task_data:
                logger.error(f"No task data found for task_key {task_key}.")
                return

            # Update the task data with the new color_poll_id
            existing_task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in existing_task_data.items()}
            existing_task_data['color_poll_id'] = str(color_poll_id)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=existing_task_data)
            self.r.expire(task_key, 86400)  # Expire after 24 hours

            # Log the updated task data for debugging
            logger.info(f"Updated task data in Redis with color_poll_id: {existing_task_data}")

            # Update the database with the new color_poll_id
            task_id = existing_task_data.get('task_id')
            if task_id:
                try:
                    conn = psycopg2.connect(**DATABASE_CONFIG)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE myapp_task_status
                        SET color_poll_id = %s
                        WHERE task_id_id = %s
                    """, [color_poll_id, task_id])  # Update the database task record with color_poll_id
                    conn.commit()
                    conn.close()
                    logger.info(f"Successfully saved shrimp color poll ID {color_poll_id} to database.")
                except Exception as e:
                    logger.error(f"Error updating database with color_poll_id: {e}")
                    raise
            else:
                logger.error(f"Task ID not found in the existing task data for task_key {task_key}.")

        except Exception as e:
            logger.error(f"Error sending shrimp color poll: {e}")
            raise




    def shrimp_color_poll_response(self, update: Update, context: CallbackContext):
        try:
            # Log the received update for debugging
            logger.info(f"Received update: {update}")
            
            # Extract poll answer details
            poll_answer = update.poll_answer
            color_poll_id = poll_answer.poll_id  # Get the color poll ID
            selected_option = poll_answer.option_ids  # Get the selected option(s) (list of indices)

            # Shrimp color options
            shrimp_color_options = ["Red", "Green", "Blue", "Yellow"]
            selected_color = [shrimp_color_options[i] for i in selected_option]

            # Log the selected shrimp color(s)
            logger.info(f"Received response for poll_id: {color_poll_id} - Selected shrimp color(s): {selected_color}")

            # Fetch all task keys in Redis and iterate over them to find the matching color_poll_id
            task_keys = self.r.keys("task_status:*")  # Fetch all task keys in Redis
            matched_task = None

            for task_key in task_keys:
                # Get the task data for the current task_key
                task_data = self.r.hgetall(task_key)

                if not task_data:
                    continue

                # Convert task data to a dictionary (from bytes to strings)
                task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

                # Check if the current task has the matching color_poll_id
                if task_data.get('color_poll_id') == color_poll_id:
                    matched_task = task_data
                    break

            if not matched_task:
                logger.error(f"No task found for color_poll_id {color_poll_id}.")
                return

            # Extract the task_id from the matched task
            task_id = matched_task.get('task_id')
            group_id = matched_task.get('group_id')

            if not task_id:
                logger.error(f"Task ID not found in matched task data for color_poll_id {color_poll_id}.")
                return

            logger.info(f"Task ID for color_poll_id {color_poll_id}: {task_id}")

            # Update the shrimp color in the matched task data
            matched_task['shrimp_color'] = ", ".join(selected_color)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=matched_task)
            self.r.expire(task_key, 86400)  # Expire in 24 hours

            # Log the updated task data in Redis for debugging
            logger.info(f"Updated task data in Redis with shrimp_color: {matched_task}")

            # Update the shrimp_color in the database
            try:
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                # Update the database task record with the shrimp_color
                cur.execute("""
                    UPDATE myapp_task_status
                    SET shrimp_color = %s
                    WHERE task_id_id = %s
                """, [", ".join(selected_color), task_id])  # Update with selected shrimp color
                conn.commit()
                conn.close()
                # Log successful database update
                logger.info(f"Successfully saved shrimp color response to database for task_id {task_id}.")
                self.send_disease_poll(group_id, matched_task, task_key)
            except Exception as e:
                logger.error(f"Error updating database with shrimp color response: {e}")
                raise

        except Exception as e:
            logger.error(f"Error processing shrimp color poll answer: {e}")
            raise






    def send_disease_poll(self, group_id, task_data, task_key):
        try:
            # Send the disease poll (Yes/No)
            disease_poll = bot.send_poll(
                chat_id=group_id,  # Using the provided chat_id
                question="Do you have any symptoms of the disease?",  # The poll question
                options=["Yes", "No"],  # Disease options (Yes/No)
                is_anonymous=False,  # User's answers are visible
                allows_multiple_answers=False  # Only one answer allowed
            )

            # Get the disease_poll_id from the sent poll
            dieses_poll_id = disease_poll.poll.id
            logger.info(f"Sent disease poll with dieses_poll_id: {dieses_poll_id}")

            # Fetch the existing task data from Redis using the task_key
            existing_task_data = self.r.hgetall(task_key)

            if not existing_task_data:
                logger.error(f"No task data found for task_key {task_key}.")
                return

            # Convert bytes to string for easier handling
            existing_task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in existing_task_data.items()}

            # Update the task data with the new disease_poll_id
            existing_task_data['dieses_poll_id'] = str(dieses_poll_id)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=existing_task_data)
            self.r.expire(task_key, 86400)  # Expire after 24 hours

            # Log the updated task data for debugging
            logger.info(f"Updated task data in Redis with disease_poll_id: {existing_task_data}")

            # Update the database with the new disease_poll_id
            task_id = existing_task_data.get('task_id')
            if task_id:
                try:
                    conn = psycopg2.connect(**DATABASE_CONFIG)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE myapp_task_status
                        SET dieses_poll_id = %s
                        WHERE task_id_id = %s
                    """, [dieses_poll_id, task_id])  # Update the database task record with dieses_poll_id
                    conn.commit()
                    conn.close()
                    logger.info(f"Successfully saved disease poll ID {dieses_poll_id} to database.")
                except Exception as e:
                    logger.error(f"Error updating database with dieses_poll_id: {e}")
                    raise
            else:
                logger.error(f"Task ID not found in the existing task data for task_key {task_key}.")

        except Exception as e:
            logger.error(f"Error sending disease poll: {e}")
            raise

    def shrimp_dieses_poll_response(self, update: Update, context: CallbackContext):
        try:
            # Log the received update for debugging
            logger.info(f"Received update: {update}")
            
            # Extract poll answer details
            poll_answer = update.poll_answer
            dieses_poll_id = poll_answer.poll_id  # Get the disease poll ID
            selected_option = poll_answer.option_ids  # Get the selected option(s) (list of indices)

            # Disease options
            disease_options = ["Yes", "No"]
            selected_answer = [disease_options[i] for i in selected_option]

            # Log the selected answer(s)
            logger.info(f"Received response for poll_id: {dieses_poll_id} - Selected answer(s): {selected_answer}")

            # Fetch all task keys in Redis and iterate over them to find the matching disease_poll_id
            task_keys = self.r.keys("task_status:*")  # Fetch all task keys in Redis
            matched_task = None

            for task_key in task_keys:
                # Get the task data for the current task_key
                task_data = self.r.hgetall(task_key)

                if not task_data:
                    continue

                # Convert task data to a dictionary (from bytes to strings)
                task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

                # Check if the current task has the matching dieses_poll_id
                if task_data.get('dieses_poll_id') == dieses_poll_id:
                    matched_task = task_data
                    break

            if not matched_task:
                logger.error(f"No task found for dieses_poll_id {dieses_poll_id}.")
                return

            # Extract the task_id from the matched task
            task_id = matched_task.get('task_id')
            group_id = matched_task.get('group_id')

            if not task_id:
                logger.error(f"Task ID not found in matched task data for dieses_poll_id {dieses_poll_id}.")
                return

            logger.info(f"Task ID for dieses_poll_id {dieses_poll_id}: {task_id}")

            # Update the disease status in the matched task data
            matched_task['diesese'] = ", ".join(selected_answer)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=matched_task)
            self.r.expire(task_key, 86400)  # Expire in 24 hours

            # Log the updated task data in Redis for debugging
            logger.info(f"Updated task data in Redis with disease_status: {matched_task}")

            # Update the disease_status in the database
            try:
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                # Update the database task record with the disease_status
                cur.execute("""
                    UPDATE myapp_task_status
                    SET diesese = %s
                    WHERE task_id_id = %s
                """, [", ".join(selected_answer), task_id])  # Update with selected disease status
                conn.commit()
                conn.close()
                # Log successful database update
                logger.info(f"Successfully saved disease status response to database for task_id {task_id}.")
                self.send_moulting_poll(group_id, matched_task, task_key)
            except Exception as e:
                logger.error(f"Error updating database with disease status response: {e}")
                raise

        except Exception as e:
            logger.error(f"Error processing disease poll answer: {e}")
            raise



    def send_moulting_poll(self, group_id, task_data, task_key):
        try:
            # Send the moulting poll (Yes/No)
            moulting_poll = bot.send_poll(
                chat_id=group_id,  # Using the provided chat_id
                question="Is the shrimp moulting?",  # The poll question
                options=["Yes", "No"],  # Moulting options (Yes/No)
                is_anonymous=False,  # User's answers are visible
                allows_multiple_answers=False  # Only one answer allowed
            )

            # Get the moulting_poll_id from the sent poll
            moulting_poll_id = moulting_poll.poll.id
            logger.info(f"Sent moulting poll with moulting_poll_id: {moulting_poll_id}")

            # Fetch the existing task data from Redis using the task_key
            existing_task_data = self.r.hgetall(task_key)

            if not existing_task_data:
                logger.error(f"No task data found for task_key {task_key}.")
                return

            # Convert bytes to string for easier handling
            existing_task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in existing_task_data.items()}

            # Update the task data with the new moulting_poll_id
            existing_task_data['moulting_poll_id'] = str(moulting_poll_id)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=existing_task_data)
            self.r.expire(task_key, 86400)  # Expire after 24 hours

            # Log the updated task data for debugging
            logger.info(f"Updated task data in Redis with moulting_poll_id: {existing_task_data}")

            # Update the database with the new moulting_poll_id
            task_id = existing_task_data.get('task_id')
            if task_id:
                try:
                    conn = psycopg2.connect(**DATABASE_CONFIG)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE myapp_task_status
                        SET moulting_poll_id = %s
                        WHERE task_id_id = %s
                    """, [moulting_poll_id, task_id])  # Update the database task record with moulting_poll_id
                    conn.commit()
                    conn.close()
                    logger.info(f"Successfully saved moulting poll ID {moulting_poll_id} to database.")
                except Exception as e:
                    logger.error(f"Error updating database with moulting_poll_id: {e}")
                    raise
            else:
                logger.error(f"Task ID not found in the existing task data for task_key {task_key}.")

        except Exception as e:
            logger.error(f"Error sending moulting poll: {e}")
            raise

        
    def shrimp_moulting_poll_response(self, update: Update, context: CallbackContext):
        try:
            # Log the received update for debugging
            logger.info(f"Received update: {update}")
            
            # Extract poll answer details
            poll_answer = update.poll_answer
            moulting_poll_id = poll_answer.poll_id  # Get the moulting poll ID
            selected_option = poll_answer.option_ids  # Get the selected option(s) (list of indices)

            # Moulting options
            moulting_options = ["Yes", "No"]
            selected_answer = [moulting_options[i] for i in selected_option]

            # Log the selected answer(s)
            logger.info(f"Received response for poll_id: {moulting_poll_id} - Selected answer(s): {selected_answer}")

            # Fetch all task keys in Redis and iterate over them to find the matching moulting_poll_id
            task_keys = self.r.keys("task_status:*")  # Fetch all task keys in Redis
            matched_task = None

            for task_key in task_keys:
                # Get the task data for the current task_key
                task_data = self.r.hgetall(task_key)

                if not task_data:
                    continue

                # Convert task data to a dictionary (from bytes to strings)
                task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

                # Check if the current task has the matching moulting_poll_id
                if task_data.get('moulting_poll_id') == moulting_poll_id:
                    matched_task = task_data
                    break

            if not matched_task:
                logger.error(f"No task found for moulting_poll_id {moulting_poll_id}.")
                return

            # Extract the task_id from the matched task
            task_id = matched_task.get('task_id')
            group_id = matched_task.get('group_id')

            if not task_id:
                logger.error(f"Task ID not found in matched task data for moulting_poll_id {moulting_poll_id}.")
                return

            logger.info(f"Task ID for moulting_poll_id {moulting_poll_id}: {task_id}")

            # Update the moulting status in the matched task data
            matched_task['moulting'] = ", ".join(selected_answer)

            # Save the updated task data back to Redis
            self.r.hset(task_key, mapping=matched_task)
            self.r.expire(task_key, 86400)  # Expire in 24 hours

            # Log the updated task data in Redis for debugging
            logger.info(f"Updated task data in Redis with moulting_status: {matched_task}")

            # Update the moulting_status in the database
            try:
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                # Update the database task record with the moulting_status
                cur.execute("""
                    UPDATE myapp_task_status
                    SET moulting = %s
                    WHERE task_id_id = %s
                """, [", ".join(selected_answer), task_id])  # Update with selected moulting status
                conn.commit()
                conn.close()
                # Log successful database update
                logger.info(f"Successfully saved moulting status response to database for task_id {task_id}.")
                # bot.send_message(group_ id=group_id, text="Thank You For Your Response. Have a Nice Day.")
            except Exception as e:
                logger.error(f"Error updating database with moulting status response: {e}")
                raise

        except Exception as e:
            logger.error(f"Error processing moulting poll answer: {e}")
            raise   

        

    def find_the_data(self):
        while True:
            try:
                current_time = datetime.now().strftime('%H:%M')
                keys = self.r.keys("task:*")
                logger.info(f"Current time: {current_time}, Keys: {keys}")
                for key in keys:
                    task_data = self.r.hgetall(key)
                    if task_data[b'from_time'].decode('utf-8') == current_time:
                        task = key.decode('utf-8').split(":")[-1]
                        if task:
                            worker_name = task_data[b'worker_name'].decode('utf-8')
                            task_name = task_data[b'category_name'].decode('utf-8')
                            option1 = task_data[b'option1'].decode('utf-8')
                            option2 = task_data[b'option2'].decode('utf-8')
                            from_time = task_data[b'from_time'].decode('utf-8')
                            to_time = task_data[b'to_time'].decode('utf-8')
                            date = task_data[b'date'].decode('utf-8')
                            pond_id = task_data[b'pond_id'].decode('utf-8')
                            group_id = task_data[b'group_id'].decode('utf-8')
                            task_id = task_data[b'task_id'].decode('utf-8')
                            args = {
                                "worker_name": worker_name,
                                "task_name": task_name,
                                "options": [option1, option2],
                                "from_time": from_time,
                                "to_time": to_time,
                                "date": date,
                                "pond_id": pond_id,
                                "group_id": group_id,
                                "task_id": task_id,
                            }
                            self.send_poll(**args)
                            logger.info(args)
                time.sleep(60)  # Check tasks every 60 seconds
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5)  # Retry after 5 seconds if there is a connection error
            except Exception as e:
                logger.error(f"Error in find_the_data: {e}")
                
                
# # Main execution point
if __name__ == "__main__":
    command = Command()
    command.handle()  # Start the bot (handles incoming messages, poll answers, etc.)
