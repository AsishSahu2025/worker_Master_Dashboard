import requests
from django.conf import settings

def send_otp_sms(phone_number, otp_code):
    api_key = settings.TWOFACTOR_API_KEY
    print("ok",phone_number, otp_code)
    url = f'https://2factor.in/API/V1/{api_key}/SMS/{phone_number}/{otp_code}'
    response = requests.get(url)
    if response.status_code == 200:
        return True
    else:
        return False