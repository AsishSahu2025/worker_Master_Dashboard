# from django.core.mail import send_mail
# import uuid
# from django.conf import settings

# def send_forget_password_mail(email, reset_token):
#     token = str(uuid.uuid4())
#     subject = 'Your forgot password link:'
#     print("oooooooooooooook")
#     # message = f'Hi.. click on the link to reset your password http://127.0.0.1:8000/changepassword/6775777877/'
#     message = f'Hi.. click on the link to reset your password http://192.168.1.66:8000/myhtml/{reset_token}'
#     email_from = settings.EMAIL_HOST_USER
#     recipient_list = [email]
#     send_mail(subject, message, email_from, recipient_list)
#     return True


# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.conf import settings



# def send_forget_password_mail(email, token):
#     subject = 'Reset Your Password'
#     try:
#         html_content = render_to_string('home.html', {'reset_password_url': f'http://127.0.0.1:8000/forgotpassword/{token}/'})
#         text_content = strip_tags(html_content)
 
#         email_from = settings.EMAIL_HOST_USER
#         recipient_list = [email]

#         msg = EmailMultiAlternatives(subject, text_content, email_from, recipient_list)
#         msg.attach_alternative(html_content, "text/html")
#         msg.send()
#         print("Email sent successfully")
#     except Exception as e:
#         print("Error:", e)