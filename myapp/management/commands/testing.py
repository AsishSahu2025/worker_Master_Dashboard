from django.core.management.base import BaseCommand
from time import sleep
from myapp.views import remote_sensing_data  # Adjust the import according to your app structure
from django.utils import timezone
from django.core.mail import send_mail
from ...models import *
from django.conf import settings
class Command(BaseCommand):
    help = 'Run remote sensing data processing every 5 days'

    def handle(self, *args, **options):
        while True:
            try:
                ponds = Pond.objects.all()
                for pond in ponds:
                    user_email = pond.registration.user.Email
                    email_subject = 'Remote Sensing Data Processing Started'
                    email_message = f"""
                    Dear User,
                        The remote sensing data processing for pond '{pond.latlong}' has started.We will notify once is complete.

                        Regards,
                        Bariflolabs
                        """
                    send_mail(
                        email_subject,
                        email_message,
                        settings.EMAIL_HOST_USER, 
                        [user_email], 
                        fail_silently=False,
                    )
                    
                    print("Email sent to", user_email)

                    super_users = Super.objects.all()
                    for super_user in super_users:
                        email_message_super = f"""
                        Dear Admin,
                            The remote sensing data processing for pond '{pond.latlong}' has started.We will notify once is complete.

                            Regards,
                            Bariflolabs
                            """
                        send_mail(
                            email_subject,
                            email_message_super,
                            settings.EMAIL_HOST_USER, 
                            [super_user.Email],
                            fail_silently=False,
                        )
                        print("Email sent to", super_user.Email)


                remote_sensing_data()
                self.stdout.write(self.style.SUCCESS("Remote sensing data processed."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            
            sleep(5 * 24 * 60 * 60)
            # sleep(60)