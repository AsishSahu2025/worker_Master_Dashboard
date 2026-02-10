# import time
# from django.contrib.auth.backends import ModelBackend
# from .models import Registration
# from django.utils import timezone
# from .models import FailedLoginAttempt

# class CustomBackend(ModelBackend):
#     MAX_FAILED_ATTEMPTS = 3
#     LOCKOUT_TIME = 60  

#     def authenticate(self, request, Mob=None, password=None, **kwargs):
#         user = Registration.objects.filter(Mob=Mob).first()
#         if user:
#             if user.password == password:  # Using the provided password field directly
#                 # Reset failed login attempts if login successful
#                 FailedLoginAttempt.objects.filter(registration=user).delete()
#                 return user
#             if self.is_account_locked(user):
#                 return None  # Account is locked
#             else:
#                 # Log failed login attempt
#                 failed_attempts = FailedLoginAttempt.objects.filter(registration=user, timestamp__gte=timezone.now() - timezone.timedelta(minutes=1)).count()
#                 if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
#                     self.lock_account(user)
#                 else:
#                     FailedLoginAttempt.objects.create(registration=user)
#         return None

#     def is_account_locked(self, user):
#         return FailedLoginAttempt.objects.filter(registration=user, timestamp__gte=timezone.now() - timezone.timedelta(seconds=self.LOCKOUT_TIME)).exists()

#     def lock_account(self, user):
#         # Lock the account by setting a lockout timestamp
#         FailedLoginAttempt.objects.create(registration=user)
#         time.sleep(self.LOCKOUT_TIME)