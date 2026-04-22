from django.db import models
from myapp.models import *

# Create your models here.

class ChecktrayTask(models.Model):
    YES_NO_CHOICES=(("YES","YES"),("No","No"))
    device_id = models.ForeignKey(Device, on_delete=models.CASCADE)
    worker_name = models.ForeignKey(Worker_details,on_delete=models.CASCADE,null=True,blank=True)
    # manager_id = models.ForeignKey(Manager)
    spray_cycle= models.CharField(choices=YES_NO_CHOICES, max_length=4, null=True, blank=True)
    image_update= models.CharField(choices=YES_NO_CHOICES,max_length=4, null=True, blank=True)
    water_level= models.FloatField(default=0)
    start_time= models.DateTimeField(null=True, blank=True)
    stop_time= models.DateTimeField(null=True, blank=True)
    status= models.CharField(max_length=100, default='Pending')
    submit= models.CharField(max_length=10, default='False')
    notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Task-{self.id} | Device-{self.device_id}"
    
    class Meta:
        indexes = [
            models.Index(fields=["device_id", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["start_time"]),
        ]
    def save(self, *args, **kwargs):
        import traceback

        if self.status == "Device Disconnected, Status Unknown":
            print("\n🚨 WHO IS SETTING DISCONNECTED?")
            traceback.print_stack()

        super().save(*args, **kwargs)


class Image(models.Model):
    IMAGE_TYPE_CHOICES = (
        ("color", "Color"),
        ("thermal", "Thermal"),
    )

    STORAGE_TYPE_CHOICES = (
        ("azure", "Azure"),
        ("local", "Local"),
    )
     
    device_id = models.CharField(max_length=30, db_index=True)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES)
    storage_mode = models.CharField(max_length=10, choices=STORAGE_TYPE_CHOICES)
    logical_path = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.image_type} | {self.created_at}"
