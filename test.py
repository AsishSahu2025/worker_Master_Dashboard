# test.py
import os
import django

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water.settings')
django.setup()

# Now you can import your models
from myapp.models import Pond

# Your test code here
def run_tests():
    # Example: Fetch all Department_Name objects
    departments = Pond.objects.all()
    for department in departments:
        print(department.name)

if __name__ == "__main__":
    run_tests()





# telegram - bot is 13.13