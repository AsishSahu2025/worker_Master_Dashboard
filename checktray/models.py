from django.db import models
from myapp.models import *

# Create your models here.

class ChecktrayTask(models.Model):
    YES_NO_CHOICES=(("YES","YES","No","No"))
    device_id = models.ForeignKey(Device, on_delete=models.CASCADE)
    cycle_no= models.IntegerField()
    sparay_cycle= models.CharField(YES_NO_CHOICES, max_length=4, null=True, blank=True)
    image_update= models.CharField(YES_NO_CHOICES,max_length=4, null=True, blank=True)
    water_level= models.FloatField(default=0)
    start_time= models.TimeField(null=True, blank=True)
    complete_time= models.TimeField(null=True, blank=True)
    status= models.CharField(max_length=30, default='Pending')
    
    def __str__(self):
        return f"Task-{self.id} | Device-{self.device_id}"

