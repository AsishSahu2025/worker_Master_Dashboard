
import datetime
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
import time
from twilio.rest import Client
from myapp.models import Task  # Adjust the import based on your app name

class Command(BaseCommand):
    help = 'Make a Twilio call based on Task schedule'

    def handle(self, *args, **kwargs):
        while True:
            current_time = datetime.datetime.now()
            target_time = (current_time + datetime.timedelta(minutes=5)).strftime('%H:%M')
            today = timezone.now().date()

            tasks = Task.objects.filter(date=today, from_time=target_time)
            
            for task in tasks:
                worker = task.worker_name
                if worker and worker.mobno:
                    self.stdout.write(f'Making call to {worker.name} ({worker.mobno}) for task {task.name}')
                    call_sid = self.twilio_call(worker.mobno, task.name)
                    if call_sid:
                        self.stdout.write(self.style.SUCCESS(f'Twilio call completed successfully, Call SID: {call_sid}'))
                    else:
                        self.stdout.write(self.style.ERROR('Twilio call failed.'))

            time.sleep(60)

    def twilio_call(self, to_number, task_name):
        try:
            account_sid = "AC0c0fc47f60af13b8ff33e2bb507dc77d"
            auth_token = "8ac73b4b22ae1c41f13d0b70ab7226d6"
            client = Client(account_sid, auth_token)
            twiml_message = f'<Response><Say>Hello. Your task "{task_name}" will start after five minutes. Be ready, thank you. Goodbye.</Say><Hangup/></Response>'
            call = client.calls.create(
                twiml=twiml_message,
                to=f'+91{to_number}',  
                from_='+919124562924'
            )       

            self.stdout.write(f'Twilio call SID: {call.sid}')
            return call.sid
        except Exception as e:
            self.stderr.write(f'Error in Twilio call: {str(e)}')
            return str(e)
