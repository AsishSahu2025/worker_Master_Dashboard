from django.core.management.base import BaseCommand
from datetime import datetime
import time, threading
import redis
import logging
from telegram.ext import Updater, CommandHandler, PollAnswerHandler, PollHandler, MessageHandler, Filters, CallbackContext
from telegram import Bot, Update, error
import psycopg2 
from django.db import transaction
from typing import Optional, Dict, Any
import telegram
from django.conf import settings
# Define CustomRequest class directly here
class CustomRequest(telegram.utils.request.Request):
   def __init__(
       self,
       con_pool_size: int = 50,
       proxy_url: Optional[str] = None,
       urllib3_proxy_kwargs: Optional[Dict[str, Any]] = None,
       connect_timeout: Optional[float] = None,
       read_timeout: Optional[float] = None,
   ):
       super().__init__(
           con_pool_size=con_pool_size,
           proxy_url=proxy_url,
           urllib3_proxy_kwargs=urllib3_proxy_kwargs,
           connect_timeout=connect_timeout,
           read_timeout=read_timeout,
       )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token and group ID
# TOKEN = '6995943945:AAEYlcaF5CTYZMSvyQ7cvCn9vbIxJic0y90'
TOKEN = '7726805789:AAHQp-T3osqTCXUOcLzS9qHSPfq8puHQoLI'
# GROUP_ID = '-4257567635'

YOUR_REDIS_HOST = settings.REDIS_HOST
YOUR_REDIS_PASSWORD = settings.REDIS_PASSWORD
YOUR_REDIS_PORT = settings.REDIS_PORT

DATABASE_CONFIG = {
   'host':settings.DATABASES['default']['HOST'],
   'database':settings.DATABASES['default']['NAME'],
   'user':settings.DATABASES['default']['USER'],
   'password':settings.DATABASES['default']['PASSWORD'],
}


# Create bot and updater instances
bot = Bot(token=TOKEN, request=CustomRequest(con_pool_size=50))
updater = Updater(bot=bot, use_context=True)

class Command(BaseCommand):
   help = 'Run the Telegram bot'
   
   def __init__(self) -> None:
       super().__init__()
       self.r = None
       self.connect_redis()
       self.start_data_finding_thread()

   def connect_redis(self):
       try:
           self.r = redis.Redis(host=YOUR_REDIS_HOST, port=YOUR_REDIS_PORT, db=0,password=YOUR_REDIS_PASSWORD, ssl=True)
           self.r.ping()
           logger.info("Connected to Redis")
       except redis.ConnectionError as e:
           logger.error(f"Redis connection error: {e}")
           raise e

   def start_data_finding_thread(self):
       thread = threading.Thread(target=self.find_the_data, daemon=True)
       thread.start()

   def handle(self, *args, **options):
       dispatcher = updater.dispatcher
       dispatcher.add_handler(PollHandler(self.poll_response))
       dispatcher.add_handler(MessageHandler(Filters.location, self.ask_location))
       updater.start_polling()
       # updater.idle()

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
           poll_id = message.poll.id
           group_id = kwargs['group_id']
           
           # Set the group id and poll id in Redis 
           self.r.hset(f"poll:{poll_id}", "group_id", group_id)
           self.r.expire(f"poll:{poll_id}", 86400)
           # Insert into Task_status table using raw SQL
           conn = psycopg2.connect(**DATABASE_CONFIG)
           print("connected")
           cur = conn.cursor() 
           cur.execute("""
               INSERT INTO myapp_task_status (name, time, date, latitude, longitude, status, username, pond_id_id, task_id_id, message_id, poll_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           """, [
               task_name, '', date, '', '', '', worker_name, pond_id, task_id, message_id, poll_id
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
               'poll_id': poll_id,
           }
           task_data = {key: str(value) for key, value in task_status.items()}
           self.r.hset(f"task_status:{poll_id}", mapping=task_data)
           self.r.expire(f"task_status:{poll_id}", 86400)
           
       except Exception as e:
           logger.error(f"Error sending poll: {e}")
           raise

   def poll_response(self, update: Update, context: CallbackContext):
       poll_data = update.poll
       poll_id = poll_data.id
       options = poll_data.options
       for option in options:
           text = option.text
           voter_count = option.voter_count

           if voter_count == 1:
               try:
                   # Fetch the task status from Redis
                   task_status_key = f"task_status:{poll_id}"
                   task_status = self.r.hgetall(task_status_key)
                   if not task_status:
                       logger.error(f"Task_status with poll_id {poll_id} does not exist in Redis.")
                       return
                   
                   current_time = datetime.now().strftime("%H:%M")
                   status = 'Yes' if text == "Yes" else 'No'
                   
                   task_status['status'] = status
                   task_status['time'] = current_time
                   self.r.hmset(task_status_key, task_status)  # Save the updated status to Redis

                   # Update the Task_status table in the database
                   conn = psycopg2.connect(**DATABASE_CONFIG)
                   cur = conn.cursor()
                   cur.execute("""
                       UPDATE myapp_task_status
                       SET status = %s, time = %s
                       WHERE poll_id = %s
                   """, [status, current_time, poll_id])
                   conn.commit()
                   conn.close()
                   
                   extracting_group_id = self.r.hget(f"poll:{poll_id}", "group_id")
                   extracted_group_id = int(extracting_group_id.decode("utf-8"))
                   print(extracted_group_id)

                   # Send a response message based on the vote
                   if text == "Yes":
                       time.sleep(1)
                       bot.send_message(chat_id=extracted_group_id, text="Please, Share your current location !!!")
                   elif text == "No":
                       time.sleep(1)
                       bot.send_message(chat_id=extracted_group_id, text="Response Captured, Thank You. \nHave a good day !!!")

               except Exception as e:
                   logger.error(f"Error handling poll response: {e}")
                   return
               
   @transaction.atomic
   def ask_location(self, update: Update, context: CallbackContext):
       username = update.message.from_user.username
       location = update.message.location
       latitude = location.latitude
       longitude = location.longitude
       try:
           # Assuming `self.r` is an instance of a Redis client
           task_keys = self.r.keys("task_status:*")
           # Sort the keys to get the latest one
           sorted_task_keys = sorted(task_keys)

           # Iterate over sorted keys in reverse order to find the latest matching task
           for key in reversed(sorted_task_keys):
               task_data = self.r.hgetall(key)
               # Convert byte strings to regular strings
               task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}
               
               if task_data.get('status') == 'Yes' and task_data.get('username') == username:
                   # Update the latitude and longitude for the latest matching task
                   self.r.hset(key, mapping={'latitude': latitude, 'longitude': longitude})
                   break
               else:
                   continue
           # Fetch the latest task status for the user
           conn = psycopg2.connect(**DATABASE_CONFIG)
           cur = conn.cursor()
           cur.execute("""
               SELECT id FROM myapp_task_status
               WHERE username = %s
               ORDER BY id DESC
               LIMIT 1
           """, [username])
           result = cur.fetchone()

           if result:
               task_status_id = result[0]
               cur.execute("""
                   UPDATE myapp_task_status
                   SET latitude = %s, longitude = %s
                   WHERE id = %s
               """, [latitude, longitude, task_status_id])
               conn.commit()
               bot.send_message(chat_id=update.effective_chat.id, text=f"{username}, Location saved successfully, Thank You.")
           else:
               logger.error(f"Task_status for {username} does not exist.")
               bot.send_message(chat_id=update.effective_chat.id, text="Error: Task_status not found.")

           conn.close()

       except Exception as e:
           logger.error(f"Error updating location: {e}")
           bot.send_message(chat_id=update.effective_chat.id, text="An error occurred while saving the location. Please try again.")

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

# Main execution point
if __name__ == "__main__":
   Command().handle()




@csrf_exempt
def myhtml(request, token):
    if request.method == "POST":
        password = request.POST.get('password')
        
        try:
            # Retrieve the user based on the reset token
            submit = User.objects.get(reset_token=token)

            # Update the local password
            submit.set_password(password)  # Use set_password to hash the password
            submit.save()

            # Connect to external database
            param = {
                'host': settings.COMMONLOGIN_DB_HOST,
                'database': settings.COMMONLOGIN_DB_NAME,
                'user': settings.COMMONLOGIN_DB_USER,
                'password': settings.COMMONLOGIN_DB_PASS
            }
            conn = psycopg2.connect(**param)
            cur = conn.cursor()

            # Update the password in the external database
            cur.execute('UPDATE public.myapp_user SET password = %s WHERE "Mobno" = %s;', (submit.password, submit.Mob))
            conn.commit()

            return JsonResponse({'message': 'Password updated successfully'})

        except User.DoesNotExist:
            return JsonResponse({'message': 'Invalid token'}, status=404)
        except Exception as e:
            # Log the exception for debugging
            print(f'Error occurred: {e}')
            return JsonResponse({'message': 'An error occurred'}, status=500)

        finally:
            # Ensure proper resource cleanup
            if cur:
                cur.close()
            if conn:
                conn.close()

    return HttpResponse('Method not allowed', status=405)