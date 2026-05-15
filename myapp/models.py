from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.gis.db import models

#********************************************** MASTER MODEL ****************************************************#
class Master(models.Model):
    Name=models.CharField(max_length=50)
    Email=models.EmailField()
    Mobno=models.BigIntegerField(primary_key=True)
    password=models.CharField(max_length=50)
    created_at=models.DateTimeField(auto_now_add=True)
    customer_id=models.CharField(max_length=100)                               
    token = models.CharField(max_length=100,blank=True, null=True)
    address = models.CharField(max_length=100)
    USER_TYPES = (
        ('3d', '3d'),
        ('analytics', 'analytics'),
        ('aqua', 'aqua'),
        ('water', 'water'),
    )
    user_category = models.CharField(max_length=30, choices=USER_TYPES,default=USER_TYPES)
    def __str__(self):
        return self.Name 


#********************************************** SUPER MODEL ****************************************************#
class Super(models.Model):
    Name = models.CharField(max_length=30)
    Mob = models.BigIntegerField(primary_key=True,unique=True)
    Email = models.EmailField()
    password=models.CharField(max_length=50)
    avtar = models.ImageField(upload_to='avtar/',default='avtar/avtar.png')
    
    def __str__(self):
        return str(self.Name)


#********************************************** USER MODEL ****************************************************#
class User(models.Model):
    adharno = models.CharField(max_length=12,null=True,blank=True)
    father_name = models.CharField(max_length=50,null=True,blank=True)
    mother_name = models.CharField(max_length=50,null=True,blank=True)
    certificateno = models.CharField(max_length=50,null=True,blank=True)
    dist = models.CharField(max_length=50,null=True,blank=True)
    state =  models.CharField(max_length=50,null=True,blank=True)
    pin = models.CharField(max_length=6,null=True,blank=True)
    Name=models.CharField(max_length=50)            
    Company_name=models.CharField(max_length=30,null=False,blank=True)
    
    country_code = models.CharField(max_length=5, default="+91")
    Mob=models.BigIntegerField(primary_key=True)
    
    Email=models.EmailField(unique=True,null=True,blank=True)
    Customer_id=models.CharField(max_length=100,null=True,blank=True)
    password = models.CharField(max_length=300)
    address=models.TextField(blank=True, null=True)
    Pan_no = models.CharField(max_length=50,blank=True, null=True)
    GST_no = models.CharField(max_length=50,blank=True, null=True)
    user_category = models.CharField(max_length=50 ,null=True,blank=True)                 
    token = models.CharField(max_length=200,blank=True,null=True)
    def save(self, *args, **kwargs):
        if not self.password.startswith('argon2$'):
            self.password = make_password(self.password)
        return super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return f"{self.Name}"
    
#********************************************** MANAGER MODEL ****************************************************#
class Manager(models.Model):
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=50 ,null=True,blank=True)
    Mob = models.BigIntegerField(primary_key=True)
    email = models.EmailField()
    USER_TYPES = (
        ('Aquafarming', 'Aquafarming'),
        ('WaterBody', 'WaterBody'),  
    )
    user_category = models.CharField(max_length=50, default="Aquafarming",choices=USER_TYPES) 
    token=models.CharField(max_length=100,null=True,blank=True)   
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.username} ({self.Mob})"
    
#********************************************** CLUSTER MODEL **************************************************#
class Cluster(models.Model):
    id = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='clusters')
    def __str__(self):
        return str(self.Name)

#********************************************** DRAW MODEL ****************************************************#
class Draw(models.Model):
    data = models.JSONField(null=True,blank=True)
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
#********************************************** POND MODEL ****************************************************#
class Pond(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    latlong = models.CharField(max_length=150)
    location = models.GeometryField(null=True, blank=True)
    timezone = models.CharField(max_length=100,default="Asia/Kolkata")
    area = models.CharField(max_length=150, blank=True,null=True)
    address = models.CharField(max_length=150)
    telegram_group_id = models.CharField(max_length=100, null=True,blank=True)
    device_quantity = models.JSONField(default=dict)
    registration = models.ForeignKey(Cluster,on_delete=models.CASCADE,related_name='ponds')
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return str(self.name)

   
#********************************************** DEVICE MODEL ****************************************************#
class Device(models.Model):
    device_id = models.CharField(max_length=255, primary_key=True)  
    maxCycles=models.IntegerField(null =True ,blank = True)
    created_at = models.DateTimeField(auto_now_add=True)
    device_type = models.CharField(max_length=100)
    pond_id = models.ForeignKey(Pond, on_delete=models.CASCADE,related_name='device')
 
    def __str__(self):
        return str(self.device_id)

 
#********************************************** PARAMETER MODEL **************************************************#
class Parameter(models.Model):
    pH = models.FloatField(null=True, blank=True)
    dissolved_oxygen = models.FloatField(null=True, blank=True)
    NDVI = models.FloatField(null=True, blank=True)
    NDTI = models.FloatField(null=True, blank=True)
    GCI = models.FloatField(null=True, blank=True)                           
    NDCI = models.FloatField(null=True, blank=True)
    NDWI = models.FloatField(null=True, blank=True)
    TSS = models.FloatField(null=True, blank=True)
    CDOM = models.FloatField(null=True, blank=True)
    AQUATIC_MACROPYTES = models.FloatField(null=True, blank=True)
    Phycocyanin = models.FloatField(null=True, blank=True)
    Chl_a = models.FloatField(null=True, blank=True)  # Add this field for Chlorophyll-a
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.pond)

############################ Service Payment Model ##################################
class ServicePayment(models.Model):
    user_name = models.CharField(max_length=100,verbose_name='User Name')
    pond_id = models.ForeignKey(Pond,on_delete=models.CASCADE)
    service_name = models.CharField(max_length=50,verbose_name='Service Name',null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    order_id = models.CharField(max_length=100, blank=True,null=True,verbose_name='Order Id')
    token = models.CharField(max_length=200,blank=True,null=True,verbose_name='Token')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user_name)

############################ FailedLoginAttempt Payment ##################################
class FailedLoginAttempt(models.Model):
    registration = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"Failed login attempt for {self.registration.Name} at {self.timestamp}"


#********************************************* Task_Category MODEL ***************************************************#s
class Task_Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
          name=f"{self.name}"
          return name
    
class Worker_details(models.Model):
    mobno = models.BigIntegerField(primary_key=True,unique=True)
    name = models.CharField(max_length=100)
    # user = models.ForeignKey(User,on_delete=models.CASCADE,max_length=100)
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, null=True, blank=True)
    manager=models.ForeignKey(Manager,on_delete=models.DO_NOTHING,max_length=100)
    def __str__(self):
          name=f"{self.name}"
          return name
    
class Task(models.Model):
    taskcatagory = models.ForeignKey(Task_Category, on_delete=models.CASCADE)
    device = models.ForeignKey(Device,on_delete=models.CASCADE)
    worker_name = models.CharField(max_length=50,null=True,blank=True)
    cycles = models.IntegerField()
    from_time = models.TimeField(null=True, blank=True)
    to_time = models.TimeField(null=True, blank=True)
    auto_feed_rate = models.CharField(max_length=255,default=100) 
    auto_sprinkle_rate = models.CharField(max_length=255,default=1000)
    auto_door=models.IntegerField(default=3000)
    feedin=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    feedin_percentage=models.IntegerField(null=True,blank=True)
    feed_weight = models.IntegerField(blank=True, null=True)
    restfeed=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    time_interval = models.CharField(max_length=20,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    schedule_date = models.DateField(null=True, blank=True)
    worker_call_notified = models.BooleanField(default=False)
    status = models.CharField(
    max_length=20,
    default="pending",
    choices=(
        ("pending", "Pending"),
        ("scheduled", "Scheduled"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("aborted", "Aborted"),
        ("unknown State", "Unknown State")
        )
    )
    is_published = models.BooleanField(default=False)
    extra_feed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    batch_id = models.UUIDField(null=True, blank=True, db_index=True)
    spray_type = models.CharField(max_length=50, blank=True, null=True)
    image=models.ImageField(upload_to='image/',null=True,blank=True)
    depth=models.CharField(max_length=100,null=True,blank=True)
    quantity = models.CharField(max_length=100, null=True,blank=True)

    def __str__(self):
        return f"Task-{self.id} | Device-{self.device_id}"


class Task_status(models.Model):
    pond_id = models.ForeignKey(Pond,on_delete=models.CASCADE)
    task_id = models.ForeignKey(Task,on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    time = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    username = models.CharField(max_length=100)
    message_id = models.BigIntegerField()
    time_poll_id = models.BigIntegerField()
    size_poll_id = models.BigIntegerField(null=True, blank=True)
    color_poll_id = models.BigIntegerField(null=True, blank=True)
    dieses_poll_id = models.BigIntegerField(null=True, blank=True)
    moulting_poll_id = models.BigIntegerField(null=True, blank=True)
    shrimp_size = models.CharField(max_length=50,null=True, blank=True)
    shrimp_color = models.CharField(max_length=50,null=True, blank=True)
    diesese = models.CharField(max_length=50,null=True, blank=True)
    moulting = models.CharField(max_length=50,null=True, blank=True)
    def __str__(self):
          name=f"{self.name}"
          return name


from django.db import models



class PhotoSubmission(models.Model):
    PHOTO_TYPES = [
    ("truck", "Truck"),
    ("received_chalan", "Received Chalan"),
    ("chalan", "Chalan"),
    ("shrimp_boxes", "Shrimp Boxes"),
]
    user_id = models.BigIntegerField()
    photo_file_id = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo_type = models.CharField(max_length=50, choices=PHOTO_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

#################################### CycleStatus MOdel ##########################################
class CycleStatus(models.Model):
    device=models.ForeignKey(Device,on_delete=models.CASCADE, related_name='cycle')
    starttime=models.DateTimeField(auto_now=True)
    cycles=models.CharField(max_length=2)
    def __str__(self):

        return 'id'
################################# Alert Message #######################################
class Alert_message(models.Model):
    device_id = models.CharField(max_length=100, null=True, blank=True)  
    alert = models.CharField(max_length=255) 
    Timestamp = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"[{self.device_id}] {self.alert}"
##################################### DeviceCommandState #########################################
class DeviceCommandState(models.Model):
    device_id = models.CharField(max_length=50,unique=True)
    task_id=models.IntegerField(null=True,blank=True)
    timepergm=models.DecimalField(max_digits=10,decimal_places=5,default=0.00125)
    step = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.step}"



##################################### BankDetails Model #########################################
class Bank_Details(models.Model):
    user = models.ForeignKey('User',on_delete=models.CASCADE ,related_name="banks")
    accountholder = models.CharField(max_length=50)
    bankname = models.CharField(max_length=50)
    ifsccode = models.CharField(max_length=11)
    branchname = models.CharField(max_length=50)
    accno = models.CharField(max_length=18)
    
    def __str__(self):
        return self.accountholder


##################################### Temp Mail Model #########################################

class EmailOTP(models.Model): 
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)     
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(auto_now=True)
    data = models.JSONField()

    def __str__(self):
        return self.email
    

##################################### Temp Mail Model #########################################
class PhoneVerification(models.Model):
    phone = models.CharField(max_length=15,unique=True)
    is_verified = models.BooleanField(default=False)
    data = models.JSONField()
    

    def __str__(self):
        return self.phone