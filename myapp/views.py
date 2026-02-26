#
from django.shortcuts import render,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import *
from rest_framework.parsers import JSONParser
from django.contrib.gis.measure import D
from django.middleware import csrf
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
# from .helper import send_forget_password_mail
import redis
from django.middleware.csrf import get_token
import psycopg2
from rest_framework.decorators import api_view
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError
from .redis_utils import get_redis_connection
from django.db.models import Prefetch
#-------------------------------------------------
from rest_framework.views import APIView
from .serializers import *
from rest_framework.response import Response
from rest_framework import status

  
#***********User Registration********#
########################################
@api_view(['POST'])
@csrf_exempt        
def user_registration(request):
    if request.method == 'POST':
        try:
            # Incoming request data
            firstname = request.data.get('firstname')
            lastname = request.data.get('lastname')
            email = request.data.get('email')
            mob = request.data.get('mobno')
            password = request.data.get('password')

            # Additional required fields
            company_name = request.data.get('company_name')
            address = request.data.get('address')
            pan_no = request.data.get('Pan_no')
            gst_no = request.data.get('GST_no')
            customer_id = request.data.get('customer_id')
            user_category= request.data.get('user_category')
            full_name = f"{firstname} {lastname}"
            print(user_category)
            if user_category==None or user_category=='':
                print('************')
                user_category="Aquafarming"

            ########################################################
            #********Function to Create table if not exists********#
            ########################################################
            
            # Create authentication token
            token = get_token(request)

            # Save to Django database
            user_obj = User(
                Name=full_name,
                Company_name=company_name,
                Mob=mob,
                Email=email,
                Customer_id=customer_id,
                user_category=user_category,
                password=password,
                address=address,
                Pan_no=pan_no,
                GST_no=gst_no,
                token=token,
            )
            user_obj.save()

            # Save to external PostgreSQL DB
            param = {
                'host': settings.COMMONLOGIN_DB_HOST,
                'database': settings.COMMONLOGIN_DB_NAME,
                'user': settings.COMMONLOGIN_DB_USER,
                'password': settings.COMMONLOGIN_DB_PASS
            }

            conn = psycopg2.connect(**param)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO public.myapp_user
                ("Name","Email", "Mob", "password",
                 "Customer_id", "Company_name","user_category",
                 "address", "Pan_no", "GST_no", "token")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
            """, (full_name,email,mob,password,customer_id,company_name,user_category,address,pan_no,gst_no,token))
            conn.commit()
            conn.close()

            return JsonResponse({"message": "User successfully registered"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        
    
        
@csrf_exempt
def cluster_create(request):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)
        name = jsondata.get('name')
        mobile = jsondata.get('mob')
        try:
            user = User.objects.get(Mob=mobile)
            name = Cluster.objects.create(Name=name,user=user)
            data = {
                "cluster_name": name.Name,
                "cluster_id": name.id,
                "customer_id" :user.Customer_id
            }
            return JsonResponse({'message':'cluster created successfully', "message": data }, status=200)
            
        except User.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'message': 'An error occurred: ' + str(e)}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)        
            

@csrf_exempt
def cluster_get(request,Mob):
    if not Mob:
            return JsonResponse({"error": "Mobile number not provided"})

    if not Manager.objects.filter(Mob=Mob):
        return JsonResponse({"error": "Mobile number not found"})
    
    if request.method == 'GET':
        clusters = Cluster.objects.all()
        # serializer = ClusterSerializer(clusters, many=True)
        return JsonResponse(clusters, safe=False)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
        

@csrf_exempt
def PondCreateView(request):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)

        name = jsondata.get('name')
        latitude = jsondata.get('latitude')
        longitude = jsondata.get('longitude')
        polygon_points = jsondata.get('location', None)
        clusterid = jsondata.get('clusterid')
        area = jsondata.get('area')
        address = jsondata.get('address')

        try:
            register_instance = Cluster.objects.get(id=clusterid)

            with transaction.atomic():

                xx = Pond(
                    name=name,
                    registration=register_instance,
                    area=area,
                    address=address
                )

                # polygon
                if polygon_points:
                    points_str = ', '.join(
                        [f'{point[0]} {point[1]}' for point in polygon_points]
                    )
                    points_str += f', {polygon_points[0][0]} {polygon_points[0][1]}'
                    xx.location = f'POLYGON(({points_str}))'
                else:
                    xx.location = None

                # lat long
                xx.latlong = f'({latitude},{longitude})'

                #  SAVE pond
                xx.save()

                return JsonResponse(
                    {
                        "message": "Pond created successfully",
                        "pond_id": xx.id
                    },
                    status=201
                )

        except Cluster.DoesNotExist:
            return JsonResponse({'message': 'Cluster not found'}, status=404)

        except IntegrityError as e:
            return JsonResponse(
                {'message': 'Database integrity error', 'error': str(e)},
                status=400
            )

        except Exception as e:
            return JsonResponse(
                {'message': 'An error occurred', 'error': str(e)},
                status=500
            )


        
        
@csrf_exempt
def viewuser(request, id):
    if request.method == 'GET':
        
        
        if not id:
            return JsonResponse({"error": "customer_id  not provided"})
       
        users = User.objects.get(Customer_id=id)
        print(users)
        data = []
        user_data = {
            'company_name': users.Company_name,
            'email': users.Email,
            'mob': users.Mob,
            'address': users.address,
        #    'user_category':users.user_category,
            'pan_no':users.Pan_no,
            'gst_no': users.GST_no,
            'customer_id':users.Customer_id,
            'password': users.password
        }
        data.append(user_data)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=400)
        

@api_view(['GET'])
def viewuser_all(request):
    if request.method == 'GET':
        users = User.objects.all()
        data = []
        for i in users:
            data.append({
                'company_name': i.Company_name,
                'email': i.Email,
                'Mob': i.Mob,
                'address': i.address,
               'user_category': i.user_category,
                'pan_no': i.Pan_no,
                'gst_no': i.GST_no,
                'customer_id': i.Customer_id,
                'password': i.password
            })
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=400)
   
    
@csrf_exempt
def userponds(request, registration_id):
    if request.method == 'GET':
        
        result = Pond.objects.filter(registration_id=registration_id)

        coordinates = []
        for item in result:
            polygon = item.location
            if polygon:  
                exterior_coords = polygon[0].coords
            else:
                exterior_coords = None  

            coordinates.append({
                'name': item.name,
                'id': item.id,
                'location': exterior_coords  
            })

        if coordinates:
            return JsonResponse({'ponds': coordinates})
        else:
            return JsonResponse({'message': 'No pond locations found for the given registration ID'}, status=404)
        
@csrf_exempt
def userpondsid(request, id):
    if request.method == 'GET':
        try:
            pond = Pond.objects.get(id=id)
            response_data = {
            'id': pond.id,
            'name': pond.name,
            'address':pond.address,
            'location': pond.location.coords,
            'area':pond.area,
        }
            return JsonResponse(response_data)
           
        except ObjectDoesNotExist:
            return JsonResponse({'message': 'Pond location not found'}, status=404)
    else:
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
   
@csrf_exempt
def admin_cluster_view(request, mob):
    if request.method == 'GET':  
        if not mob:
           return JsonResponse({"error": "mob not provided"})
        # users = User.objects.get(Mob=mob)
        try:
            users = User.objects.get(Mob=mob)
            print(users, "User found")
            data = []
            # Fetch all clusters associated with this user
            clusters = Cluster.objects.filter(user=users)
            for cluster in clusters:
                data.append({
                    "Name":cluster.Name,
                    "id":cluster.id,
                    "Mob":users.Mob
                })
            return JsonResponse(data, safe=False)

        except User.DoesNotExist:
            # If not found in User, try fetching from Manager table
            try:
                managers = Manager.objects.get(Mob=mob)
                # Use the manager's related user instance
                users = managers.user  # Assuming Manager has a ForeignKey to User model
                print(managers, "Manager found, using the related User")
                data = []
                # Fetch all clusters associated with the user linked to the manager
                clusters = Cluster.objects.filter(user=users)
                for cluster in clusters:
                    data.append({
                        "Name":cluster.Name,
                        "id":cluster.id,
                        "Mob":users.Mob
                    })
                return JsonResponse(data, safe=False)

            except Manager.DoesNotExist:
                return JsonResponse({"error": "mob not found in User or Manager tables"}, status=404)
      
    else:
        return JsonResponse({"message": "Invalid request method"}, status=405)
   
   
@csrf_exempt
def adminpond_view(request,id):
    print(id)
    if request.method == 'GET':
        
        if not id:
            return JsonResponse({"error": "id not provided"})
        try:
            user = User.objects.all()
            managerss = Manager.objects.all()
            value = Cluster.objects.get(id=id)
            pond = Pond.objects.filter(registration=value)
            data = []
            for i in pond:
                data.append({
                    "id":i.id,
                    "name":i.name,
                    "latlong":i.latlong,
                    "area":i.area,
                #    "telegram_group_id":i.telegram_group_id,
                    "registration":i.registration.Name,
                    "address":i.address      
                })
               
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error":str(e)})
       

@csrf_exempt
def deviceregistry_view(request,customer_id):
    if request.method == "GET":
        
        
        try:
            if not customer_id:
                return JsonResponse({"error": "customer_id not provided"})
            
            user = User.objects.get(Customer_id=customer_id)
            print(user)
            data =[]
            cluster = Cluster.objects.filter(user=user)
            print(cluster)
            for i in cluster:
                print(i)
                pond = Pond.objects.filter(registration=i)
                print(pond)
                print("byyyy")
                for j in pond:
                    print(j)
                    data.append({
                        "name":user.Company_name,
                        "device":j.device_quantity
                    #     "id":i.id,
                    #     "name":i.name,
                    #     "latlong":i.latlong,
                    #     "area":i.area,
                    # #    "telegram_group_id":i.telegram_group_id,
                    #     "registration":i.registration.Name,
                    #     "city":i.city      
                    })
                    print(data)
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error":str(e)})
        

@csrf_exempt
def send_location(request,id):
    if request.method == 'GET':        
        try:
            managers = Manager.objects.all()
            cluster = Cluster.objects.get(id=id)
            ponds = Pond.objects.filter(registration=cluster)
            
            response = []
            for pond in ponds:
                pond_data = {
                    'name': pond.name,
                    'pond_location': pond.location.coords if pond.location else [],
                }
                response.append(pond_data)

            return JsonResponse(response, safe=False)
        except Cluster.DoesNotExist:
            return JsonResponse({'message': 'Cluster not found'}, status=404)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    

@csrf_exempt
def drawline(request):
    if request.method == 'POST':
        try:
            jsondata = JSONParser().parse(request)
            id = jsondata.get('id')
            data = jsondata.get('data')

            if not id or not data:
                return JsonResponse({'message': 'ID and data are required'}, status=400)

            cluster = Cluster.objects.get(id=id)
            existing_draw = Draw.objects.filter(cluster=cluster).first()

            if existing_draw:
                existing_draw.delete()

            # Create the new Draw instance
            Draw.objects.create(data=data, cluster=cluster)
            print("Draw instance created")
            return JsonResponse({'message': 'Data saved successfully'}, status=201)

        except Cluster.DoesNotExist:
            return JsonResponse({'message': 'Cluster not found'}, status=404)
        except Exception as e:
            print("Exception:", e)
            return JsonResponse({'message': 'Error occurred while saving data.'}, status=500)
        
    elif request.method == 'GET':
        cluster_id = request.GET.get('id')
        if not cluster_id:
            return JsonResponse({'message': 'ID query parameter is required'}, status=400)
        try:
            data = Draw.objects.get(cluster__id=cluster_id)
            return JsonResponse({'data': data.data}, status=200) 
        except Draw.DoesNotExist:
            return JsonResponse({'message': 'No data found for the given cluster ID'}, status=404)
        except Exception as e:
            print("Exception:", e)
            return JsonResponse({'message': 'Error occurred while retrieving data.'}, status=500)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt
def deviceregistry_all(request):
    if request.method == 'GET':
        users = User.objects.all()  
        data = []  
        for user in users:
            clusters = Cluster.objects.filter(user=user)  # Fetch clusters for each user
            for cluster in clusters:
                ponds = Pond.objects.filter(registration=cluster)  
                for pond in ponds:
                    devices = Device.objects.filter(pond_id=pond)        
                    for device in devices:
                        data.append({
                            "Company_name": user.Company_name,
                            "device": device.device_id,  # Device ID
                            "name": device.device_type.name,  # Device type name from DeviceType model
                            "pond_id": device.pond_id_id,  # Pond ID
                        })
        return JsonResponse(data, safe=False)  # Return all collected data as a JSON response
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    
 
@csrf_exempt
def devicedetails_add(request):
    if request.method == 'POST':
        # Parse data from the POST request body
        name = request.POST.get('name')  # Get the 'name' from the form data
        image = request.FILES.get('image')
        if not image and name:
            return JsonResponse({'error': 'Name and image are required'}, status=400)
        try:
            DeviceType.objects.create(name=name, image=image)
            return JsonResponse({'message': 'Device type created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Use POST instead.'}, status=405)
 
            
          
@csrf_exempt
def devicedetails_get(request): 
    if request.method == 'GET':
        managers = Manager.objects.all()
        feeding = DeviceType.objects.filter(name="Feeding").first()
        feedtray = DeviceType.objects.filter(name='Feed Tray').first()
        
        other_device_types = DeviceType.objects.exclude(name__in=["Feeding", "Feed Tray"])

        data = []
        if feeding:
            data.append({
                'name': feeding.name,
                'image': feeding.image.url if feeding.image else None
            })
        if feedtray:
            data.append({
                'name': feedtray.name,
                'image': feedtray.image.url if feedtray.image else None
            })
        for detail in other_device_types:
            data.append({
                'name': detail.name,
                'image': detail.image.url if detail.image else None
            })
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
            

@csrf_exempt
def master_registration(request):
    if request.method == 'POST':
        regd_instance=JSONParser().parse(request)
        firstname=regd_instance.get('firstname')
        lastname=regd_instance.get('lastname')
        email=regd_instance.get('email')
        mobno=regd_instance.get('mobno')
        address=regd_instance.get('address')
        user_cat=regd_instance.get('user_cat')
        password=regd_instance.get('params')
        fullname=firstname+" "+lastname
        instance=Master.objects.filter(Mobno=mobno)
        
        try:
            if not instance.exists():
                token = get_token(request)
                datas = Master(Name=fullname,Email=email,Mobno=mobno,password=password,address=address,user_category=user_cat,reset_token=token)
                datas.save()
                return JsonResponse({"massage":"master creation Successfull"})
            else:
                return JsonResponse({"massage":"Mobile number already registered, Report to Bariflo cyber"})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def master_common_login(request):
   try:
       jsondata = JSONParser().parse(request)
       Mobno = jsondata.get('Mobno')

       if not Mobno:
           return JsonResponse({'message': 'Mobile number is required'}, status=400)

       try:
           master = Master.objects.get(Mobno=Mobno)
           response_data = {
               'Mob': master.Mobno,
               'name': master.Name,
               'email': master.Email,
               'cat': 'master'
           }
           return JsonResponse(response_data, safe=False)
       except User.DoesNotExist:
           admin = Super.objects.filter(Mobno=Mobno).first()
           if admin:
               return JsonResponse({'cat': 'admin','Mobno':admin.Mobno}, safe=False)
           else:
               return JsonResponse({'message': 'User not found'}, status=404)

   except Exception as e:
       return JsonResponse({'message': f'Error: {str(e)}'}, status=400)
   
   
   
@csrf_exempt
def common_login(request):
    try:
        # Parse JSON data
        jsondata = JSONParser().parse(request)
        Mob = jsondata.get('Mob')

        if not Mob:
            return JsonResponse({'message': 'Mobile number is required'}, status=400)

        # ----------------------------------------
        # 1. CHECK IN MASTER TABLE
        # ----------------------------------------
        try:
            master = Master.objects.get(Mobno=Mob)
            response_data = {
                'Mob': master.Mobno,
                'name': master.Name,
                'email': master.Email,
                'category': 'master'
            }
            return JsonResponse(response_data, status=200)
        except Master.DoesNotExist:
            pass

        # ----------------------------------------
        # 2. CHECK IN USER TABLE
        # ----------------------------------------
        try:
            user = User.objects.get(Mob=Mob)   # make sure mob exists
            print(user)

            serializer = UserCluserSerializer(user)

            response_data = {
                'message': 'You have successfully logged in to the owner page...',
                'Mob': user.Mob,
                'name': user.Company_name,
                'email': user.Email,
                'user_category': user.user_category,
                'category': 'owner',
                'cluster': serializer.data
            }

            return JsonResponse(response_data, status=200)


        except User.DoesNotExist:
            pass

        # ----------------------------------------
        # 3. CHECK IN MANAGER TABLE
        # ----------------------------------------
        try:
            manager = Manager.objects.get(Mob=Mob)
            users = manager.user  # FK to User model
            
            response_data = {
                'message': 'You have successfully logged in to the Manager page...',
                'Mob': manager.Mob,
                'name': manager.username,
                'email': manager.email,
                'user_category': users.user_category,
                'category': 'manager'
            }
            return JsonResponse(response_data, status=200)

        except Manager.DoesNotExist:
            return JsonResponse(
                {'message': 'No master/user/manager found with this mobile number'},
                status=404
            )

    except Exception as e:
        return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)

    
# from .backends import CustomBackend
# import time

# # Define a dictionary to keep track of login attempts
# login_attempts = {}

# @csrf_exempt
# def login(request):
#     if request.method == 'POST':
#         userdata = JSONParser().parse(request)
#         identifier = userdata.get('identifier')
#         password = userdata.get('password')

#         def is_valid_email(identifier):
#             return "@" in identifier

#         try:
#             if is_valid_email(identifier):
#                 admins = Master.objects.filter(Email=identifier, password=password)
#             else:
#                 admins = Master.objects.filter(Mobno=identifier, password=password)

#             if admins.exists():
#                 csrf_token = csrf.get_token(request)
#                 admin = admins.first()
#                 response_data = {
#                     'message': 'You are successfully entered the Master page...',
#                     'Mob': admin.Mobno,
#                     'name': admin.Name,
#                     'password': password,
#                     'email': admin.Email,
#                     'csrf_token': csrf_token,
#                     "category":"Master"
#                 }
#                 return JsonResponse(response_data, status=200)

#         except ObjectDoesNotExist:
#             pass

#         try:
#             if is_valid_email(identifier):
#                 users = User.objects.filter(Email=identifier, password=password)
#             else:
#                 users = User.objects.filter(Mob=identifier, password=password)

#             if users.exists():
#                 csrf_token = csrf.get_token(request)
#                 user = users.first()
#                 response_data = {
#                     'message': 'You are successfully logged in to the Manager page ....',
#                     'Mob': user.Mob,
#                     'name': user.Company_name,
#                     'email': user.Email,
#                     'csrf_token': csrf_token,
#                     'category':"Manager"
                    
#                 }
#                 return JsonResponse(response_data, status=200)

#         except ObjectDoesNotExist:
#             pass

#         return JsonResponse({'message': 'Invalid credentials'}, status=400)

#     return JsonResponse({'message': 'Invalid request method'}, status=400)

# @csrf_exempt
# def myhtml(request, token):
#     if request.method == "POST":
#         password = request.POST.get('password')

#         conn = None  # Initialize to avoid UnboundLocalError
#         cur = None   # Initialize to avoid UnboundLocalError

#         try:
#             submit = User.objects.get(token=token)
#             submit.password = password
#             submit.save()

#             param = {
#                 'host': settings.COMMONLOGIN_DB_HOST,
#                 'database': settings.COMMONLOGIN_DB_NAME,
#                 'user': settings.COMMONLOGIN_DB_USER,
#                 'password': settings.COMMONLOGIN_DB_PASS
#             }

#             conn = psycopg2.connect(**param)
#             cur = conn.cursor()

#             email = submit.Email  
#             cur.execute('UPDATE public.myapp_user SET password = %s WHERE "Email" = %s;', (password, email))
#             conn.commit()
#             return JsonResponse({'message': 'Password successfully changed'}, status=200)


#         except User.DoesNotExist:
#             return JsonResponse({'message': 'Invalid token'}, status=404)
#         except Exception as e:
#             print(f'Error occurred: {e}')
#             return JsonResponse({'message': 'An error occurred'}, status=500)

#         finally:
#             if cur is not None:  # Ensure cur was assigned before closing
#                 cur.close()
#             if conn is not None:  # Ensure conn was assigned before closing
#                 conn.close()

#     return render(request, 'home.html')


# import uuid
# @csrf_exempt
# def forgotpassword(request):
#     if request.method == 'POST':
#         jsondata = JSONParser().parse(request)
#         email = jsondata.get('Email')
#         try:
#             user = User.objects.get(Email=email)
#             reset_token = user.token
#             send_forget_password_mail(email, reset_token)
#             return JsonResponse({'message': 'We send a change password link to your registered email id .Please click the link to reset password'}, status=200)
#         except ObjectDoesNotExist:
#             return JsonResponse({'message': 'Email does not exist'}, status=404)


@csrf_exempt
def changepassword(request, mob):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)
        password = jsondata.get('password')

        try:
            # Update local database
            local_user = User.objects.filter(Mob=mob)
            if local_user.exists():
                local_user.update(password=password)

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
                cur.execute('UPDATE public.myapp_user SET password = %s WHERE "Mobno" = %s;', (password, mob))

                conn.commit()

                return JsonResponse({'message': 'Password changed successfully'})
            else:
                return JsonResponse({'message': 'User not found'}, status=404)

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



import requests
from django.shortcuts import render
from django.http import JsonResponse
from .otp_service import send_otp_sms
from django.conf import settings
import random

def generate_otp():
    otp_code =  ''.join(random.choice('0123456789') for _ in range(6))
    return otp_code
@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        userdata=JSONParser().parse(request)
        phone_number = userdata.get('phone_number')
        if phone_number:
            otp_code = generate_otp()  # Function to generate OTP
            send_otp_sms(phone_number, otp_code)  # Function to send OTP via 2Factor
            print(phone_number,otp_code)
            return JsonResponse({'message': 'OTP sent successfully'})
        else:
            return JsonResponse({'error': 'Phone number not provided'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
from rest_framework.decorators import permission_classes

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permission import IsAdminOrDenied

@csrf_exempt
# @permission_classes([ IsAdminOrDenied])
def fetch_cluster(request, Mob):
    if request.method == 'GET':
        print(Mob)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission Denied: You are not an admin.'}, status=403)
        try:
            user = User.objects.get(Mob=Mob)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

        clusters = Cluster.objects.filter(user=user)
        if not clusters:
            return JsonResponse({'error': 'No clusters found for this user'}, status=404)

        cluster_list = list(clusters.values()) 
        # cluster_list = [user.Name,user.telegram_username,user.Mob]
        print(clusters.values())
        return JsonResponse(cluster_list, safe=False)

    return HttpResponse(status=405)







from django.core.files.base import ContentFile

import base64
    


@csrf_exempt
def photosend(request,id):
    if request.method == 'GET': 
        try:
            user = User.objects.get(Mob=id)
            if user:
                if user.avtar:
                    responsedata = {
                'photo': user.avtar.url,
                }
            return JsonResponse(responsedata)

        except:
            user = Super.objects.get(Mob=id)
            if user:
                if user.avtar:
                    responsedata = {
                'photo': user.avtar.url,
                }
            return JsonResponse(responsedata)
        

@csrf_exempt
def task_assign_pondlist(request,id):
    print(id)
    if request.method == 'GET':
        try:
            user = Cluster.objects.get(id=id)
            # print(user)
            ponds = Pond.objects.filter(registration=user)
           
            response = []
            for pond in ponds:
                response.append({
                    'id': pond.id,
                    'name':pond.name,
                })
               
            return JsonResponse(response, safe=False) 
        except:
            return JsonResponse({'message':'error'})  


@csrf_exempt
def pondanalytic(request, mob):
    if request.method == 'GET':
        try:
            user = User.objects.get(Mob=mob)
            clusters = Cluster.objects.filter(user=user)
    
            response = []  
            
            for cluster in clusters:
                ponds = Pond.objects.filter(registration=cluster)
            
                for pond in ponds:
                    pond_data = {
                        'id': pond.id,
                        'name': pond.name,
                        'pond_location': pond.location.coords if pond.location else [],
                        'city': pond.city,
                    }

                    devices = Device.objects.filter(account=pond)
                    if devices.exists():
                        for device in devices:
                            task_status = Task_status.objects.filter(pond_id=pond).order_by('-time').first()
                            device_data = {
                                'device_id': device.device_id,
                                'device_name': device.device_name,
                                'location': device.location,
                                'status': task_status.status if task_status else 'No status available',
                            }

                            merged_data = pond_data.copy()
                            for key, value in device_data.items():
                                if value is not None:
                                    merged_data[key] = value
                            response.append(merged_data)
                    else:
                        response.append(pond_data)

            return JsonResponse(response, safe=False)
        except User.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)




class clusterpond_analytic(APIView):
    def get(self,request,pk):
        try:
            cluster=Cluster.objects.get(pk=pk)           
            serializer=ClusterSerializer(cluster)
            return Response(serializer.data,status=200)
        except Cluster.DoesNotExist:
            return Response({'sms':"Cluser Not Found"},status=404)
    


 
    
import datetime
from redis import Redis
from datetime import datetime

@csrf_exempt
def work_assign(request):
    if request.method == 'POST':
        try:
            jsondata = JSONParser().parse(request)
            all_tasks = jsondata.get('tasks')
        
            ##### Check if 'tasks' is a list #######
            if not isinstance(all_tasks, list):
                return JsonResponse({"error": "'tasks' should be a list"}, status=400)

            ##### Update validation to expect more then 7 element  #####
            if len(all_tasks) < 8:
                return JsonResponse({"error": "Each task must have exactly 6 elements"}, status=400)
            
            task_name = all_tasks[0]  # Task Name
            time_ranges = all_tasks[1]  # Time Ranges (list of pairs)
            pond_name = all_tasks[2]  # Pond Name
            pond_id = all_tasks[3]  # Pond ID (optional)
            feed_weights = all_tasks[4]  # Feed Weight (list of feed weights)
            probiotic = all_tasks[5] # Probiotic (list of probiotic names)
            quantity = all_tasks[6] 
            worker_name = all_tasks[7]
            
            ####### Fetch the task category #######
            try:
                task_instance = Task_Category.objects.get(name=task_name)
            except Task_Category.DoesNotExist:
                return JsonResponse({"error": f"Task Category '{task_name}' not found"}, status=404)
            try:
                worker_instance = Worker_details.objects.get(name=worker_name)
            except Worker_details.DoesNotExist:
                return JsonResponse({"error": f"worker  Category '{worker_name}' not found"}, status=404)

            # Fetch the pond instance
            pond_instance = Pond.objects.filter(id=pond_id).first()
            if not pond_instance:
                return JsonResponse({"error": f"Pond '{pond_id}' not found"}, status=404)

            # Ensure feed_weights is a list and handle each feed weight
            if not isinstance(feed_weights, list):
                return JsonResponse({"error": "'feed_weights' should be a list"}, status=400)

            # Initialize Redis connection
            r = get_redis_connection()
            if r is None:
                return JsonResponse({"error": "Unable to connect to Redis"}, status=500)
                
            # Loop through the time ranges and feed_weights and create tasks
            for i, time_range in enumerate(time_ranges):
                if len(time_range) != 2:
                    continue  # Skip invalid time ranges

                from_time = time_range[0]
                to_time = time_range[1]
        
                # Handle feed weight for this task
                feed_weight = feed_weights[i] if i < len(feed_weights) else None  # Default to 0 if no feed weight
        
                # Validate feed weight
                if task_name == "Feeding":
                    if not feed_weight or feed_weight in ["None", "none"]:
                        return JsonResponse({"error": "Feed weight is required for Feeding tasks"}, status=400)
                    try:
                        feed_weight = float(feed_weight)
                    except ValueError:
                        return JsonResponse({"error": "Invalid feed weight. Please provide a valid number."}, status=400)
               
                # For non-Feeding tasks, feed weight is not mandatory
                elif not feed_weight or feed_weight in ["None", "none"]:
                    feed_weight = 0
                print(feed_weight)
                task = Task.objects.create(
                    name=task_instance,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    from_time=from_time,
                    to_time=to_time,
                    feed_weight=feed_weight,
                    pond_id=pond_instance,
                    probiotic=probiotic, # Save probiotic as a list in the database
                    quantity=quantity,
                    worker_name=worker_instance
                )
             
                # Prepare task data for Redis
                task_data = {
                    'category_name': task_instance.name,
                    'option1': "Yes",
                    'option2': "No",
                    'feed_weight': str(feed_weight),
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'from_time': from_time,
                    'to_time': to_time,
                    'pond_id': pond_instance.id,
                    'group_id': pond_instance.telegram_group_id,
                    'task_id': task.id,
                    'probiotic': probiotic,  # Adding probiotic as a list for Redis
                    'quantity': quantity,
                    "worker_name": worker_instance.name
                }

               
                # Convert task data to string values for Redis
                task_data = {key: str(value) for key, value in task_data.items()}
               
                # Generate a Redis key based on the current time
                task_key = f"task:{datetime.now().strftime('%H:%M:%S.%f')}"
            
                r.hset(task_key, mapping=task_data)
                r.expire(task_key, 360)  # Set expiry for Redis data
                print("Done")
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse({"message": "Task dataset stored in both database & Redis"})

@csrf_exempt
def category(request):
    if request.method == 'GET':
        
        try:
            result = Task_Category.objects.all()
            response = []
            for i in result:
                response.append({
                    "name" : i.name
                })
            return JsonResponse({'category':response}, safe=False)
        except:
            return JsonResponse({'category':'error'})



@csrf_exempt
def feedweight_per_date(request, mobno):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            date_param = data.get('date')
            pond_id = data.get('pond_id') 

            if not date_param:
                return JsonResponse({"message": "Please provide a date parameter in the body."}, status=400)
            if not pond_id:
                return JsonResponse({"message": "Please provide a pond_id parameter in the body."}, status=400)
            users = User.objects.filter(Mob=mobno)
            if not users:
                return JsonResponse({"message": f"No user found with Mob number: {mobno}."}, status=404)
            response_data = []

            for user in users:
                clusters = Cluster.objects.filter(user=user)
                if not clusters:
                    return JsonResponse({"message": f"No cluster found for user with Mob number: {mobno}."}, status=404)
                
                for cluster in clusters:
                    ponds = Pond.objects.filter(registration=cluster, id=pond_id)  
                    if not ponds:
                        return JsonResponse({"message": f"No pond found with pond_id: {pond_id} for the user."}, status=404)
                    for pond in ponds:
                        date = datetime.strptime(date_param, '%Y-%m-%d').date()
                        tasks = Task.objects.filter(pond_id=pond, date=date).values('feed_weight', 'created_at')
                        if tasks:
                            response_data.extend(list(tasks))
            if not response_data:
                return JsonResponse({"message": f"No feed_weight data found for Mob number {mobno} on {date_param} for pond_id {pond_id}."}, status=404)

            return JsonResponse(response_data, safe=False)
        except ValueError:
            return JsonResponse({"message": "Invalid date format. Please use YYYY-MM-DD."}, status=400)

    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)
    
    

from django.db.models import Sum
@csrf_exempt
def feedweight_per_week(request, mobno):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            date_param = data.get('date')
            pond_id = data.get('pond_id')

            if not date_param:
                return JsonResponse({"message": "Please provide a date parameter in the body."}, status=400)
            if not pond_id:
                return JsonResponse({"message": "Please provide a pond_id parameter in the body."}, status=400)
            users = User.objects.filter(Mob=mobno)
            if not users:
                return JsonResponse({"message": f"No user found with Mob number: {mobno}."}, status=404)

            response_data = []

            date = datetime.strptime(date_param, '%Y-%m-%d').date()
            start_of_week = date - timedelta(days=date.weekday())
            end_of_week = start_of_week + timedelta(days=6)  
            for user in users:
                clusters = Cluster.objects.filter(user=user)
                if not clusters:
                    return JsonResponse({"message": f"No cluster found for user with Mob number: {mobno}."}, status=404)
                
                for cluster in clusters:
                    ponds = Pond.objects.filter(registration=cluster, id=pond_id)
                    if not ponds:
                        return JsonResponse({"message": f"No pond found with pond_id: {pond_id} for the user."}, status=404)

                    for pond in ponds:
                        tasks = Task.objects.filter(pond_id=pond, date__range=[start_of_week, end_of_week])\
                                             .values('date')\
                                             .annotate(feed_weight=Sum('feed_weight'))\
                                             .order_by('date')
                        for task in tasks:
                            response_data.append({
                                'created_at': task['date'].strftime('%Y-%m-%d'),
                                'feed_weight': task['feed_weight']
                            })
            if not response_data:
                return JsonResponse({"message": f"No feed_weight data found for Mob number {mobno} in the week starting {start_of_week} for pond_id {pond_id}."}, status=404)

            return JsonResponse(response_data, safe=False)

        except ValueError:
            return JsonResponse({"message": "Invalid date format. Please use YYYY-MM-DD."}, status=400)
    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)




import calendar 
@csrf_exempt
def feedweight_per_month(request, mobno):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            month_param = data.get('month') 
            pond_id = data.get('pond_id')
            
            if not month_param:
                return JsonResponse({"message": "Please provide a month parameter in the body (format: YYYY-MM)."}, status=400)
            if not pond_id:
                return JsonResponse({"message": "Please provide a pond_id parameter in the body."}, status=400)
            
            try:
                year, month = map(int, month_param.split('-'))
                start_of_month = datetime(year, month, 1).date()
                _, days_in_month = calendar.monthrange(year, month)
                end_of_month = start_of_month + timedelta(days=days_in_month - 1)
            except ValueError:
                return JsonResponse({"message": "Invalid month format. Please use YYYY-MM."}, status=400)

            users = User.objects.filter(Mob=mobno)
            if not users:
                return JsonResponse({"message": f"No user found with Mob number: {mobno}."}, status=404)

            response_data = []
            for user in users:
                clusters = Cluster.objects.filter(user=user)
                if not clusters:
                    return JsonResponse({"message": f"No cluster found for user with Mob number: {mobno}."}, status=404)
                
                for cluster in clusters:
                    ponds = Pond.objects.filter(registration=cluster, id=pond_id)
                    if not ponds:
                        return JsonResponse({"message": f"No pond found with pond_id: {pond_id} for the user."}, status=404)

                    for pond in ponds:
                        week_start = start_of_month
                        while week_start <= end_of_month:
                            week_end = min(week_start + timedelta(days=6), end_of_month)  

                            tasks = Task.objects.filter(pond_id=pond, date__range=[week_start, week_end])\
                                                 .aggregate(feed_weight=Sum('feed_weight'))

                            if tasks['feed_weight']:
                                response_data.append({
                                    'week_start': week_start.strftime('%Y-%m-%d'),
                                    'week_end': week_end.strftime('%Y-%m-%d'),
                                    'feed_weight': tasks['feed_weight']
                                })
                            else:
                                response_data.append({
                                    'week_start': week_start.strftime('%Y-%m-%d'),
                                    'week_end': week_end.strftime('%Y-%m-%d'),
                                    'feed_weight': 0
                                })
                            week_start += timedelta(days=7)
            if not response_data:
                return JsonResponse({"message": f"No feed_weight data found for Mob number {mobno} in the month {month_param} for pond_id {pond_id}."}, status=404)

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)




from django.utils.dateparse import parse_date
@csrf_exempt
def feedweight_date(request, clusterid):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            date_param = data.get('date')

            if not date_param:
                return JsonResponse({"message": "Please provide a date parameter in the body."}, status=400)

            try:
                date = parse_date(date_param)
                if not date:
                    raise ValueError
            except ValueError:
                return JsonResponse({"message": "Invalid date format. Please use YYYY-MM-DD."}, status=400)

            response_data = []

        
            clusters = Cluster.objects.get(id=clusterid)
            if not clusters:
                return JsonResponse({"message": f"No cluster found for user with clusterid: {clusterid}."}, status=404)

            ponds = Pond.objects.filter(registration=clusters)
            if not ponds:
                return JsonResponse({"message": "No ponds found for the user's cluster."}, status=404)

            for pond in ponds:
                tasks = Task.objects.filter(pond_id=pond, date=date).values('feed_weight', 'created_at')
                pond_data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "tasks": list(tasks)
                }
                response_data.append(pond_data)

            if not response_data:
                return JsonResponse({"message": f"No data found for clusterid{clusterid} on {date_param}."}, status=404)

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)




@csrf_exempt
def feedweight_week(request, clusterid):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            date_param = data.get('date')

            if not date_param:
                return JsonResponse({"message": "Please provide a date parameter in the body."}, status=400)

            try:
                date = parse_date(date_param)
                if not date:
                    raise ValueError
            except ValueError:
                return JsonResponse({"message": "Invalid date format. Please use YYYY-MM-DD."}, status=400)

            # Calculate the start and end of the week
            start_of_week = date - timedelta(days=date.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            response_data = []


            clusters = Cluster.objects.get(id=clusterid)
            if not clusters:
                return JsonResponse({"message": f"No cluster found for user with clusterid: {clusterid}."}, status=404)

            ponds = Pond.objects.filter(registration=clusters)
            if not ponds:
                return JsonResponse({"message": f"No ponds found for the user's cluster."}, status=404)

            for pond in ponds:
                tasks = Task.objects.filter(pond_id=pond, date__range=[start_of_week, end_of_week])\
                                        .values('date')\
                                        .annotate(feed_weight=Sum('feed_weight'))\
                                        .order_by('date')

                pond_data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "tasks": [
                        {
                            "date": task['date'].strftime('%Y-%m-%d'),
                            "feed_weight": task['feed_weight']
                        }
                        for task in tasks
                    ]
                }
                response_data.append(pond_data)

            if not response_data:
                return JsonResponse({"message": f"No feed_weight data found for clusterid {clusterid} in the week starting {start_of_week}."}, status=404)

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)




@csrf_exempt
def feedweight_month(request, clusterid):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            month_param = data.get('month')

            if not month_param:
                return JsonResponse({"message": "Please provide a month parameter in the body (format: YYYY-MM)."}, status=400)

            try:
                year, month = map(int, month_param.split('-'))
                start_of_month = datetime(year, month, 1).date()
                _, days_in_month = calendar.monthrange(year, month)
                end_of_month = datetime(year, month, days_in_month).date()
            except ValueError:
                return JsonResponse({"message": "Invalid month format. Please use YYYY-MM."}, status=400)

            response_data = []

            
            clusters = Cluster.objects.get(id=clusterid)
            if not clusters:
                return JsonResponse({"message": f"No cluster found for user with clusterid: {clusterid}."}, status=404)

            
            ponds = Pond.objects.filter(registration=clusters)
            if not ponds:
                return JsonResponse({"message": "No ponds found for the user's cluster."}, status=404)

            for pond in ponds:
                week_start = start_of_month
                pond_data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "tasks": []
                }

                while week_start <= end_of_month:
                    week_end = min(week_start + timedelta(days=6), end_of_month)

                    tasks = Task.objects.filter(
                        pond_id=pond,
                        date__range=[week_start, week_end]
                    ).aggregate(feed_weight=Sum('feed_weight'))

                    pond_data["tasks"].append({
                        "week_start": week_start.strftime('%Y-%m-%d'),
                        "week_end": week_end.strftime('%Y-%m-%d'),
                        "feed_weight": tasks['feed_weight'] or 0
                    })

                    week_start += timedelta(days=7)

                response_data.append(pond_data)

            if not response_data:
                return JsonResponse({"message": f"No feed_weight data found for clusterid {clusterid} in the month {month_param}."}, status=404)

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({"message": "Invalid HTTP method, please use POST."}, status=405)





@csrf_exempt
def workerview(request, mob):
    if request.method != 'GET':
        return JsonResponse(
            {"message": "Method not allowed"},
            status=405
        )

    try:
        user = User.objects.filter(Mob=mob).first()
        manager = None

        if not user:
            manager = Manager.objects.filter(Mob=mob).first()
            if not manager:
                return JsonResponse(
                    {"message": "Not Found any Manager or Owner"},
                    status=404
                )

        if user:
            result = Worker_details.objects.filter(user=user)
        else:
            result = Worker_details.objects.filter(manager=manager)

        response = []
        for i in result:
            response.append({
                "name": i.name
            })

        return JsonResponse(
            {"Employee": response},
            status=200
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )

        
        
          
from django.shortcuts import get_object_or_404
@csrf_exempt
def live_feed_view(request, usermob):
    if request.method == "GET":
        try:
            # Get the user object
            user_data = get_object_or_404(User, Mob=usermob)
            
            # Get all clusters associated with the user
            cluster_data = Cluster.objects.filter(user=user_data)
            print(cluster_data)
            # Get all ponds associated with the clusters
            pond_data = Pond.objects.filter(registration__in=cluster_data)
            print(pond_data)
            all_new_data = []
            current_time = datetime.datetime.now().strftime("%H:%M")
            current_date = datetime.datetime.now().date()

            # Iterate over each pond to get task data
            for pond in pond_data:
                task_data = Task_status.objects.filter(
                    pond_id=pond.id,
                    time=current_time,
                    date=current_date
                )

                for task in task_data:
                    if task.status.lower() == 'yes' and task.latitude and task.longitude:
                        new_data = {
                            "NAME": str(task.name),
                            "TIME": str(task.time),
                            "LATITUDE": str(task.latitude),
                            "LONGITUDE": str(task.longitude),
                            "STATUS": str(task.status),
                            "USERNAME": str(task.username),
                            "POND_ID": str(task.pond_id),
                            "TASK_ID": str(task.task_id),
                            "MESSAGE_ID": str(task.message_id),
                            "POLL_ID": str(task.poll_id)
                        }
                        all_new_data.append(new_data)
                    elif task.status.lower() == 'no':
                        new_data = {
                            "NAME": str(task.name),
                            "TIME": str(task.time),
                            "LATITUDE": str(task.latitude),
                            "LONGITUDE": str(task.longitude),
                            "STATUS": str(task.status),
                            "USERNAME": str(task.username),
                            "POND_ID": str(task.pond_id),
                            "TASK_ID": str(task.task_id),
                            "MESSAGE_ID": str(task.message_id),
                            "POLL_ID": str(task.poll_id)
                        }
                        all_new_data.append(new_data)

            return JsonResponse(all_new_data, safe=False)

        except User.DoesNotExist:
            return JsonResponse([], safe=False)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)

        
################################################### admin side ########################################################

    

   
from django.db.models import Count
@csrf_exempt
def pondcount(request, registration_id):
    if request.method == 'GET':
        value = Cluster.objects.get(id=registration_id)
        result = Pond.objects.filter(registration_id=value) \
            .values('registration_id') \
            .annotate(num_ponds=Count('id')) \
            .values('num_ponds')  

        if result:
            return JsonResponse({'pond_counts': list(result)})
        else:
            return JsonResponse({'message': 'No pond locations found for the given registration ID'}, status=404)
        
        
@csrf_exempt
def user_delete(request,customer_id):
    if request.method == 'DELETE':    
        # if not admin_mob:
        #     return JsonResponse({"error": "admin mobile number not provided"})
        # if not Super.objects.filter(Mob=admin_mob):
        #     return JsonResponse({"error": "admin mobile number not found"})
            
        try:
            variable = User.objects.get(Customer_id=customer_id)
            print(f"Local User found: {variable}")

            # Connect to the external database
            # param = {
            #     'host': settings.COMMONLOGIN_DB_HOST,
            #     'database': settings.COMMONLOGIN_DB_NAME,
            #     'user': settings.COMMONLOGIN_DB_USER,
            #     'password': settings.COMMONLOGIN_DB_PASS
            # }
            # conn = psycopg2.connect(**param)
            # cur = conn.cursor()

            # # Use the correct field name for the external database
            # # Note: Use variable.Mob to refer to the local Mob field
            # print(f"Attempting to delete user with Mobno: {variable.Mob}")  # Change here if needed
            # cur.execute('DELETE FROM public.myapp_user WHERE "Mobno" = %s;', (variable.Mob,))
            # conn.commit()

            # # Check if the deletion was successful
            # if cur.rowcount == 0:
            #     print(f"No user found with Mobno {variable.Mob} in external DB.")
            # else:
            #     print(f'User with Mobno {variable.Mob} deleted from external DB.')

            # Now delete the user from the local database
            variable.delete()
            return JsonResponse({'message': 'User deleted successfully'}, status=200)

        except User.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
        except Exception as e:
            # Log the exception for debugging
            print(f'Error occurred: {e}')
            return JsonResponse({'message': 'An error occurred during deletion'}, status=500)
        
        # finally:
        #     # Ensure proper resource cleanup
        #     if 'cur' in locals() and cur:
        #         cur.close()
        #     if 'conn' in locals() and conn:
        #         conn.close()
    
    return JsonResponse({'message': 'Invalid request method'}, status=405)
    #         print(variable)
    #         param = {
    #             'host': settings.COMMONLOGIN_DB_HOST,
    #             'database': settings.COMMONLOGIN_DB_NAME,
    #             'user': settings.COMMONLOGIN_DB_USER,
    #             'password': settings.COMMONLOGIN_DB_PASS
    #         }
    #         print("jiii")
    #         conn = psycopg2.connect(**param)
    #         print("byy")
    #         cur = conn.cursor()
    #         print("heloo")

    #         # Delete the user from the external database using Mobno
    #         cur.execute('DELETE FROM public.myapp_user WHERE "Mobno" = %s;',  (variable.Mobno,))
    #         print("hiiii")
    #         conn.commit()
    #         print(f'User with Mobno {variable.mob} deleted from external DB.')

    #         variable.delete()
    #         return JsonResponse({'message':'user delete successfull'})
    #     except:
    #         return JsonResponse({'message':'user Already deleted'})
    #     finally:
    #         # Ensure proper resource cleanup
    #         if 'cur' in locals() and cur:
    #             cur.close()
    #         if 'conn' in locals() and conn:
    #             conn.close()
    # else:
    #     return JsonResponse({'message':'Invalid user'})
        



        
        

   
   
@csrf_exempt
def admin_cluster_delete_all(request,id):
    # print(Mob)
    if request.method == 'DELETE':
        # jsondata = JSONParser().parse(request)
        # cluster_name = jsondata.get('name')
        # print(cluster_name)
        
        # user = User.objects.get(Mob=Mob)
        # print(user)
        cluster = Cluster.objects.filter(id=id)
        print(cluster)
        
        if cluster:
            cluster.delete()
            print("hh")
            return JsonResponse({'message': 'Cluster deleted successfully'}, status=200)
        
@csrf_exempt
def admin_cluster_delete(request,id):
    # print(Mob)
    if request.method == 'DELETE':
        # jsondata = JSONParser().parse(request)
        # pond_id = jsondata.get('id')
        # print(pond_id)
        
        # user = User.objects.get(Mob=Mob)
        # print(user)
        # cluster = Cluster.objects.filter(user=user)
        # print(cluster)
        # for i in cluster:
        pond = Pond.objects.filter(id=id)
        
        if pond:
            pond.delete()
            return JsonResponse({'message': 'pond deleted successfully'}, status=200)
        
 
    
@csrf_exempt
def adminpond(request, Mob):
    if request.method == 'GET':
        try:
            data = []
            xx = Pond.objects.filter(registration=Mob)
            for i in xx:
                service = ServicePayment.objects.filter(pond_id=i)
                payment_services = [] 
                for payment in service:
                    payment_data ={
                        'service_name':payment.service_name,
                        'created_at':payment.created_at.date()
                    }
                    payment_services.append(payment_data)
                response_data = {  
                    'id': i.id ,
                    'name': i.name,
                    'area': i.area,
                    'city':i.city,
                    'payment_services': payment_services  
                }
                data.append(response_data)

            return JsonResponse(data, safe=False)
        except:
            return JsonResponse({'message': 'error'})

@csrf_exempt
def success(request):
    return render(request, "success.html")

        

@csrf_exempt
def delete_drawline(request,id):
    if request.method == 'DELETE':
        # cluster_id = Cluster.objects.filter(id=cluster_id)
        draw_id = Draw.objects.get(cluster__id=id)
        if not draw_id:
            return JsonResponse({'message': 'Draw_ID query parameter is required'}, status=400)
        draw_id.delete()
        return JsonResponse({'message': 'drwaline  deleted successfully'}, status=200)
    
###################################################### not in use ###############################################
import razorpay
@csrf_exempt
def create_order(request):                                                    # new API for razorpay from frontend
     if request.method == "POST":
        jsondata = JSONParser().parse(request)
        amount = jsondata.get('amount')  

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": "order_receipt",
            "notes": {
                "email": "user_email@example.com",
            },
        }

        order = client.order.create(data=payment_data)
        token = csrf.get_token(request)
        
        response_data = {  
            "id": order["id"],  
            "amount": order["amount"],
            "currency": order["currency"],
            "key": settings.RAZORPAY_KEY_ID,
            "name": "Your Company Name",
            "description": "Payment for Your Product",
            "image": "https://yourwebsite.com/logo.png",  
            "token": token,
        }
        # print(response_data)
        return JsonResponse(response_data)

# from .models import ServicePayment,Pond
@csrf_exempt
def complete_order(request):
    if request.method == "POST":
            jsondata = JSONParser().parse(request)
            user_name = jsondata.get('username')
            pond_id = jsondata.get('pondid')
            service_name = jsondata.get('servicename')
            amount = jsondata.get('amount')
            order_id = jsondata.get('orderid')
            token = jsondata.get('token')
            
            print(service_name,pond_id,user_name,amount,order_id,token)
            pond = Pond.objects.get(id=pond_id)
            print(service_name)
            try:
                print("complete try.......")
                payment = ServicePayment.objects.create(
                    user_name = user_name,
                    pond_id = pond,
                    service_name = service_name,
                    amount = amount,
                    order_id = order_id,
                    token = token
                )
                payment.save()
                return JsonResponse({'message': 'Payment done Successful'})
            except Exception as e:
                return JsonResponse({'message': 'error'})
                    
    else:
        return JsonResponse({'message': 'Pond location not found'}, status=404)

##################################################################################
########################## user and admin side ###################################

@csrf_exempt
def photoupload(request, Mob):
    if request.method == 'POST':
        try:
            user = User.objects.get(Mob=Mob)
            if user:
                
                photo = request.FILES.get('photo')
                if photo:
                    user.avtar = photo
                    user.save()
                    return JsonResponse({'message': 'success'})
                else:
                    return JsonResponse({'message': 'No photo provided'}, status=400)
        except:
            user = Super.objects.get(Mob=Mob)
            if user:
                
                photo = request.FILES.get('photo')
                if photo:
                    user.avtar = photo
                    user.save()
                    return JsonResponse({'message': 'success'})
                else:
                    return JsonResponse({'message': 'No photo provided'}, status=400)
        # except Exception as e:
        #     return JsonResponse({'message': str(e)}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    






from django.contrib.auth.decorators import login_required 

# @login_required
def trail(request):
    if request.method == 'GET':
        return HttpResponse("ok")


# import ee
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# ee.Initialize(project='ee-tapaskumarsahoo9090')



@csrf_exempt
def graph(request, id):
    if request.method == 'POST':
        try:
            jsondata = JSONParser().parse(request)
            month = jsondata.get('month')
            if not month:
                return JsonResponse({'message': 'Month is required'}, status=400)
            
            temp = Parameter.objects.filter(
                pond=id, 
                created_at__month=month
            ).order_by('-created_at')[:5]
            
            if temp.exists():
                ph_values = [param.pH for param in temp]
                DO_values = [param.dissolved_oxygen for param in temp]
                ndvi_values = [param.NDVI for param in temp]
                ndti_values = [param.NDTI for param in temp]
                gci_values = [param.GCI for param in temp]
                ndci_values = [param.NDCI for param in temp]
                ndwi_values = [param.NDWI for param in temp]
                TSS_values = [param.TSS for param in temp]
                cdom_values = [param.CDOM for param in temp]
                AQUATIC_MACROPYTES_values = [param.AQUATIC_MACROPYTES for param in temp]

                weeks = [f"week {(i.created_at.day - 1) // 7 + 1}" for i in temp]
                weeks.reverse()

                response = {
                    'ph': ph_values,
                    'dissolved_oxygen': DO_values,
                    'NDVI': ndvi_values,
                    'NDTI': ndti_values,
                    'GCI': gci_values,
                    'NDCI': ndci_values,
                    'NDWI': ndwi_values,
                    'TSS': TSS_values,
                    'CDOM': cdom_values,
                    'AQUATIC_MACROPYTES': AQUATIC_MACROPYTES_values,
                    'week': weeks
                }
                return JsonResponse(response ,safe = False)
            else:
                return JsonResponse({'message': 'No data found for the given month and pond'}, status=404)

        except Exception as e:
            return JsonResponse({'message': 'An error occurred', 'error': str(e)}, status=500)
            # return JsonResponse({'message': 'error', 'error': str(e)}, status=500)
        

############################################# for remote sensing ###################################


# https://console.cloud.google.com/iam-admin/serviceaccounts/details/100731980639633209130;edit=true/keys?authuser=1&project=ee-tapaskumarsahoo9090
# import ee
# from google.oauth2 import service_account 
# Define the required scopes
# SCOPES = ['https://www.googleapis.com/auth/earthengine.readonly']
# Load the credentials from the JSON key file
# credentials = service_account.Credentials.from_service_account_file(
    # 'ee-earth-engine-cloud-471609-d2c7ef4caa59.json', scopes=SCOPES)                      #for local machine uncomment this line.
    # '/app/ee-tapaskumarsahoo9090-397890d43df1.json', scopes=SCOPES)               #for docker file uncomment this line.
    
# Initialize the Earth Engine with the credentials
# ee.Initialize(credentials)
# def remote_sensing_data(request=None):
#     try:
#         ponds = Pond.objects.all()
#         for pond in ponds:
#             point_str = pond.latlong
#             coordinates = point_str.strip("()").split(",")
#             latitude, longitude = map(float, coordinates)
#             geometry = ee.Geometry.Point([longitude, latitude])``
#             print(geometry)
            
        
#             # image = ee.ImageCollection("COPERNICUS/S2_SR") \
#             image = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
#                         .filterBounds(geometry) \
#                         .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 20)) \
#                         .first()

import ee
from google.oauth2 import service_account

def init_ee():
    credentials = service_account.Credentials.from_service_account_file(
        'wired-summit-481512-p0-4fa68e53f2bf.json',
        scopes=['https://www.googleapis.com/auth/earthengine']
    )
    ee.Initialize(credentials)
    print("Earth Engine Connected")


import random
from datetime import datetime, timedelta
def remote_sensing_data():
    try:
        init_ee()
        ponds = Pond.objects.all()

        for pond in ponds:
            # ----------------------------
            # Geometry
            # ----------------------------
            lat, lon = map(float, pond.latlong.strip("()").split(","))
            geometry = ee.Geometry.Point([lon, lat])

            # ----------------------------
            # Date range (last 30 days)
            # ----------------------------
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # ----------------------------
            # Image collection
            # ----------------------------
            image_collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geometry)
                .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 40))
                .filterDate(start_date, end_date)
            )

            image_count = image_collection.size().getInfo()
            print("Available images count:", image_count)

            if image_count == 0:
                print(f"No images found for pond {pond.latlong}")
                continue

            image = ee.Image(
                image_collection.sort("system:time_start", False).first()
            )

            # ----------------------------
            # Index Calculations
            # ----------------------------
            ph = ee.Image(8.339).subtract(
                ee.Image(0.827).multiply(image.select("B1").divide(image.select("B8")))
            ).rename("pH")

            dissolved_oxygen = (
                ee.Image(-0.0167).multiply(image.select("B8"))
                .add(ee.Image(0.0067).multiply(image.select("B9")))
                .add(ee.Image(0.0083).multiply(image.select("B11")))
                .add(ee.Image(9.577))
                .rename("Dissolved_Oxygen")
            )

            ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            ndti = image.normalizedDifference(["B4", "B3"]).rename("NDTI")
            gci = image.select("B3").pow(0.5).multiply(image.select("B4")).pow(0.5).subtract(1).rename("GCI")
            ndci = image.select("B5").subtract(image.select("B4")).divide(
                image.select("B5").add(image.select("B4"))
            ).rename("NDCI")
            ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
            tss = image.select("B4").subtract(image.select("B8")).pow(2).multiply(0.6113).rename("TSS")
            cdom = image.select("B3").divide(image.select("B2")).rename("CDOM_Index")
            phycocyanin = ee.Image(26.89).multiply(
                image.select("B3").divide(image.select("B2"))
            ).subtract(27.43).rename("Phycocyanin")
            chl_a = image.select("B5").add(image.select("B6")).divide(image.select("B4")).rename("Chl-a")

            # ----------------------------
            # Reduce to mean values
            # ----------------------------
            def mean(img, band):
                return img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometry,
                    scale=10
                ).get(band).getInfo()

            data = {
                "pH": mean(ph, "pH"),
                "Dissolved Oxygen": mean(dissolved_oxygen, "Dissolved_Oxygen"),
                "NDVI": mean(ndvi, "NDVI"),
                "NDTI": mean(ndti, "NDTI"),
                "GCI": mean(gci, "GCI"),
                "NDCI": mean(ndci, "NDCI"),
                "NDWI": mean(ndwi, "NDWI"),
                "TSS": mean(tss, "TSS"),
                "CDOM": mean(cdom, "CDOM_Index"),
                "Phycocyanin": mean(phycocyanin, "Phycocyanin"),
                "Chl-a": mean(chl_a, "Chl-a"),
            }
            print(data)
            # ----------------------------
            # Save to DB
            # ----------------------------
            Parameter.objects.create(
                pond=pond,
                pH=data["pH"],
                dissolved_oxygen=data["Dissolved Oxygen"],
                NDVI=data["NDVI"],
                NDTI=data["NDTI"],
                GCI=data["GCI"],
                NDCI=data["NDCI"],
                NDWI=data["NDWI"],
                TSS=data["TSS"],
                CDOM=data["CDOM"],
                AQUATIC_MACROPYTES=data["NDVI"],
                Phycocyanin=data["Phycocyanin"],
                Chl_a=data["Chl-a"],
            )

            # ----------------------------
            # Emails
            # ----------------------------
            email_subject = "Remote Sensing Data Saved...."
            user_email = pond.registration.user.Email

            send_mail(
                email_subject,
                f"Remote sensing data saved for pond '{pond.latlong}'.",
                settings.EMAIL_HOST_USER,
                [user_email],
                fail_silently=False,
            )

            for admin in Super.objects.all():
                send_mail(
                    email_subject,
                    f"Remote sensing data saved for pond '{pond.latlong}'.",
                    settings.EMAIL_HOST_USER,
                    [admin.Email],
                    fail_silently=False,
                )

            print("Processed pond:", pond.latlong)

        return JsonResponse({"message": "Data saved successfully"})

    except Exception as e:
        print("Error:", e)
        return JsonResponse({"message": "Record not found"}, status=404)

       
# ------------------------------------------------------------------------------------------------
# API to fetch device details based on device_type.
# Returns device info along with associated pond addresses for all users and clusters.
# DEVICE DETAILS API
# ------------------------------------------------------------------------------------------------

@csrf_exempt
def device_details(request,device_type):
    if request.method == 'GET':
        try:
            # -------------------------------
            # Fetch device by device_type
            # -------------------------------
            devices = Device.objects.get(device_type=device_type)
            print(devices)
            data = []
            # -------------------------------
            # Loop through all users
            # -------------------------------
            user = User.objects.all()
            for users in user:
                # -------------------------------
                # Get clusters for the current user
                # -------------------------------
                cluster = Cluster.objects.filter(user=users)
                for clusters in cluster:
                    # -------------------------------
                    # Get ponds registered under this cluster
                    # -------------------------------
                    pond = Pond.objects.filter(registration=clusters)
                    for ponds in pond:
                        # -------------------------------
                        # Append device + pond info
                        # -------------------------------
                        data.append({
                            'device_id': devices.device_id,
                            'created_at': devices.created_at.strftime('%Y-%m-%d %H:%M:%S'),  
                            'device_type': str(devices.device_type), 
                            'address': ponds.address,
                        })
                        
            
                        return JsonResponse(data, safe=False)
        except Device.DoesNotExist:
            return JsonResponse({'error': 'Device not found'}, status=404)
    else:
        return JsonResponse({'message': 'Method not allowed'}, status=405)

 
@csrf_exempt
def get_parameters(request ,pond_id):
    if request.method == 'GET':
        try:
            pond = Pond.objects.get(id=pond_id)
            # pond = Pond.objects.filter(registration=cluster)
            response = []  
            # for i in pond:
            #     print(i)
            parameters = Parameter.objects.filter(pond=pond)
            print(parameters)
            for parameter in parameters:
                parameter_data = {
                    'NDVI': parameter.NDVI,
                    'pond':parameter.pond_id,
                    'created_at': parameter.created_at
                    
                    # 'type': parameter.type,
                    # 'unit': parameter.unit,
                }
                
                response.append(parameter_data)
            return JsonResponse(response,safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)})

# import telegram
# # bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
# from myapp.management.commands import Telegrambot_conversation
# # from myapp.models import Telegram_data
# from myapp.management.commands.Telegrambot_conversation import handle_message 
# @csrf_exempt

# # API view to handle incoming Telegram messages
# @csrf_exempt
# def telegram_bot_post(request):
#     if request.method == 'POST':
#         try:
#             data = JSONParser().parse(request)
#             user_name = data.get('user_name')
#             message = data.get('message')

#             if not user_name:
#                 return JsonResponse({'message': 'User name is required'}, status=400)

#             if not message:
#                 return JsonResponse({'message': 'Message is required'}, status=400)        
            
#             user_id = None  
#             if user_name not in user_data:
#                 return JsonResponse({'message': 'User not found'}, status=404)

#             user_id = user_data.get(user_name, {}).get('chat_id') 
#             if user_id:
#                 update = Update.de_json({
#                     'message': {
#                         'from': {'id': user_id, 'username': user_name},
#                         'text': message,
#                     },
#                 }, bot=context.bot)
                
#                 handle_message(update, CallbackContext)
#                 return JsonResponse({'message': 'Message sent successfully'})
#             else:
#                 return JsonResponse({'message': 'User ID not found in the bot system'}, status=404)

#         except Exception as e:
#             logger.error(f"Error occurred: {e}")
#             return JsonResponse({'message': 'Error occurred while sending message'}, status=500)
#     else:
#         return JsonResponse({'message': 'Invalid HTTP method'}, status=405)
# 



############################Manager############################

@csrf_exempt
def manager_details_post(request):
    if request.method == 'POST':
        try:
            # ---------------------------------------------------
            # Parse incoming JSON data from the POST request
            # ---------------------------------------------------
            data = JSONParser().parse(request)
            username = data.get('username')
            password = data.get('password')
            mob = data.get('Mob')
            email = data.get('email')
            company_name = data.get('company_name')
 
            # --------------------------------------------------------------------
            # Validate and find users associated with the given company
            # ----------------------------------------------------------------------
            users = User.objects.filter(Company_name=company_name)
            print(users)
            if not users.exists():
                return JsonResponse({'error': 'No users found for the given company'}, status=404)
            
            # ----------------------------------------------------------------
            # Iterate through all matched users and create Manager entries
            # ----------------------------------------------------------------
            for user in users:
                # Create Manager object in local database
                details = Manager.objects.create(
                    username=username,
                    password=password,
                    Mob=mob,
                    email=email,
                    user=user
                )
                details.save()

                # -------------------------------------------
                # Connect to the external database
                # -------------------------------------------
                param = {
                    'host': settings.COMMONLOGIN_DB_HOST,
                    'database': settings.COMMONLOGIN_DB_NAME,
                    'user': settings.COMMONLOGIN_DB_USER,
                    'password': settings.COMMONLOGIN_DB_PASS
                }
                try:
                    conn = psycopg2.connect(**param)
                    cur = conn.cursor()
                   
                    # --------------------------------------------------------------------
                    # Prepare and execute query to insert data into the external database
                    # ---------------------------------------------------------------------
                    insert_query = '''
                    INSERT INTO public.myapp_manager("username", "password", "Mob", "email", "user_id")
                    VALUES (%s, %s, %s, %s, %s);
                    '''
                    cur.execute(insert_query, (username, password, mob, email, user.Mob))
                    conn.commit()

                    # Close the external database connection
                    cur.close()
                    conn.close()
                    
                except (Exception, psycopg2.DatabaseError) as error:
                    # Return error if external DB operation fails
                    return JsonResponse({'error': f'Database error: {str(error)}'}, status=500)
 
            # ----------------------------------------------------
            # Return success response after all users processed
            # ----------------------------------------------------
            return JsonResponse({"message": "Registration Successful"}, status=201)
 
        except Exception as e:
            # Return any unexpected errors
            return JsonResponse({"error": str(e)}, status=500)
 
    else:
        # Return error for non-POST requests
        return JsonResponse({'message': 'Invalid HTTP method'}, status=405)

    
 
@csrf_exempt
def delete_manager(request):
    if request.method == 'DELETE':
        try:
            data = JSONParser().parse(request)
            mob = data.get('Mob')  # This is the primary key
 
            # Step 1: Delete from Django (main) DB
            try:
                manager = Manager.objects.get(Mob=mob)
                manager.delete()
            except Manager.DoesNotExist:
                return JsonResponse({'error': 'Manager not found in main DB'}, status=404)
 
            # Step 2: Delete from external DB
            param = {
                'host': settings.COMMONLOGIN_DB_HOST,
                'database': settings.COMMONLOGIN_DB_NAME,# def workerview(request,mob):
#     if request.method == 'GET':
#         try:
#             user = User.objects.filter(Mob=mob).first()
#             if user:
#                 print(user)
#             else:
#                 manager = Manager.objects.filter(Mob=mob).first()
#                 if manager:
#                     print("manager")
#                 else:
#                     return Response("Not Found any Manager or Owner", status=404)
            
#             if user:
#                 result = Worker_details.objects.filter(user=user)
#             elif manager:
#                 result = Worker_details.objects.filter(manager=manager)
#                 response = []
#                 for i in result:
#                     response.append({
#                         "name":i.name
#                     })
#                 return JsonResponse({'Employee':response}, safe=False)
#         except:
#             return JsonResponse({'category':'error'})
                'user': settings.COMMONLOGIN_DB_USER,
                'password': settings.COMMONLOGIN_DB_PASS
            }
            try:
                conn = psycopg2.connect(**param)
                cur = conn.cursor()
 
                delete_query = '''
                DELETE FROM public.myapp_manager WHERE "Mob" = %s;
                '''
                cur.execute(delete_query, (mob,))
                conn.commit()
                cur.close()
                conn.close()
            except (Exception, psycopg2.DatabaseError) as error:
                return JsonResponse({'error': f'External DB deletion error: {str(error)}'}, status=500)
 
            return JsonResponse({'message': 'Manager deleted successfully from both databases'}, status=200)
 
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
 
    else:
        return JsonResponse({'message': 'Invalid HTTP method'}, status=405)
#----------------------------------------------------------------------------------------------

class deviceid_view(APIView):
    def get(self,request,id):
        try:
            pond=Pond.objects.get(id=id)
            device_type=request.query_params.get('device_type')
            devices=Device.objects.filter(pond_id=pond)
            if device_type:
                devices=devices.filter(device_type=device_type)
            serializer=PondDeviceSerializer(pond,context={'devices':devices})
            return Response(serializer.data,status=200)
        except Pond.DoesNotExist:
            return Response("Pond Doesn't exiest")
#----------------------------------------------------------------------------------------------

class CycleStatusview(APIView):
    def post(self,request):
        serializer=CycleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"sms":f"Owner start the Machine of Device_id={serializer.validated_data['device']}"})
#----------------------------------------------------------------------------------------------
class FeedingGenerateview(APIView):
    def post(self, request):
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category_name = data['deviceName']
        device_id = data['deviceId']
        total_cycles = data['cycles']
        last_task = None
        check_sts = None
        last_task = Task.objects.filter(device=device_id).order_by('-id').first()
        if last_task != None:
            check_sts=getattr(last_task,'status')

        if  check_sts == "processing" or check_sts == "abort" or check_sts == "pending":
            return Response(f"{device_id} is on Processing.., try After completed the Process.")
        try:
            category = Task_Category.objects.get(name__iexact=category_name)
            created_task_ids = []

            with transaction.atomic():
                for cycle_no in range(1, total_cycles + 1):
                    task = Task.objects.create(
                        taskcatagory=category,  
                        device_id=device_id,
                        cycles=cycle_no,
                        from_time=None,
                        to_time=None,
                        feed_weight=None,
                        feedin=data['feedin'] if cycle_no == 1 else None,
                        feedin_percentage=100 if cycle_no == 1 else None,
                        spray_type=None,
                        time_interval=None,
                        quantity=None,
                        depth=None,
                        image=None
                    )
                    created_task_ids.append(task.id)
            return Response(
                {
                    "message": f"{total_cycles} cycles created successfully",
                    "deviceName": category.name,
                    "task_ids": created_task_ids,
                    'status':"pending"
                },
                status=status.HTTP_201_CREATED
            )
        except Task_Category.DoesNotExist:
            return Response(
                {"error": f"Task category '{category_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
#---------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------
from .validator import check_interval
import threading
class TaskSubmitview(APIView):
    def put(self,request,id):
        cycle=Task.objects.get(id=id)
        serializer=TaskSubmitSerializer(cycle,data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        task=Task.objects.get(id=id)
        #---------------------- Threading------------------------------
        threading.Thread(
            target=check_interval,
            args=(id,),
            daemon=True
        ).start()
        
        return Response({"sms":"Send to Fedding Check....","status":"processing","Remain feedin":f"{task.feedin} Kg","to_time":f"{task.to_time}","restfeed":f"{task.restfeed}","payload": "AUTO"})

# ===============================================================================================================
#                                           TASK GET Total Feed 
# ===============================================================================================================
        
class PondTaskView(APIView):

    def get(self, request):
        pond_id = request.query_params.get("pond_id")
        device_id = request.query_params.get("device_id")

        today = timezone.now().date()
        tasks = Task.objects.select_related("device").filter(
            created_at__date=today
        )

        if pond_id:
            tasks = tasks.filter(device__pond_id__id=pond_id)

        if device_id:
            tasks = tasks.filter(device__device_id=device_id)

        if not tasks.exists():
            message = "No tasks found."

            if pond_id and device_id:
                message = f"No tasks found for pond_id={pond_id} and device_id={device_id}."
            elif pond_id:
                message = f"No tasks found for pond_id={pond_id}."
            elif device_id:
                message = f"No tasks found for device_id={device_id}."

            return Response({"message": message}, status=200)

        tasks = tasks.order_by("cycles")

        serializer = PondTaskSerializer(tasks, many=True)

        return Response(
            {
                "pond_id": pond_id,
                "device_id": device_id,
                "total_tasks": tasks.count(),
                "tasks": serializer.data,
            },
            status=200,
        )

#----------------------------------------------------------------------------------------------
class Abortview(APIView):
    def post(self,request,id):
        task=Task.objects.get(id=id)
        serializer=AbortSerializer(task,data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"sms":"Abert the Process Sucessfuly....","status":"Abort"})
#----------------------------------------------------------------------------------------------

class Restartview(APIView):
    def put(self,request,id):
        task=Task.objects.get(id=id)
        serializer=TaskSubmitSerializer(task,data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"sms":"Send to Chick Feeding Again....","status":"processing"})
#--------------------------------------------------------------------------------------------

class FeedTryGenerateview(APIView):
    def post(self, request):
        serializer = FeedTryGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category_name = data['deviceName']
        device_id = data['deviceId']
        total_cycles = data['cycleCount']
        start_time = data['startTime']        # time object
        interval = data['hour_format']        # total hours

        interval_per_cycle = interval / total_cycles

        try:
            category = Task_Category.objects.get(name__iexact=category_name)

            cycles_data = []

            base_datetime = datetime.combine(datetime.today(), start_time)

            with transaction.atomic():
                for cycle_no in range(1,total_cycles+1):
                    task_datetime = base_datetime + timedelta(
                        hours=interval_per_cycle * cycle_no
                    )

                    task = Task.objects.create(
                        taskcatagory=category,
                        device_id=device_id,
                        cycles=cycle_no ,
                        from_time=None,
                        to_time=None,
                        feed_weight=None,
                        feedin=None,
                        feedin_percentage=None,
                        spray_type=data['spray_type'],
                        time_interval=task_datetime.time(),
                        depth=None,
                        image=None,
                        quantity=None,
                        status="processing"
                    )

                    start_t = task_datetime.time()
                    end_t = (task_datetime + timedelta(hours=interval_per_cycle)).time()

                    cycles_data.append({
                        "cycleNo": cycle_no,
                        "taskId": task.id,
                        "cycleName": f"C{cycle_no}", 
                        "image": None,
                        "depth": 0,
                        "time_interval": f"{start_t.strftime('%-H:%M')} - {end_t.strftime('%-H:%M')}",
                        "status": task.status
                    })

            return Response(
                {
                    "message": f"{total_cycles} cycles created successfully",
                    "deviceName": category.name,
                    "deviceId": device_id,
                    "cycle": cycles_data
                },
                status=status.HTTP_201_CREATED
            )

        except Task_Category.DoesNotExist:
            return Response(
                {"error": f"Task category '{category_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
#---------------------------------------------------------------------------------------

###################################### Publish FIRST Message and abort ################################
import paho.mqtt.client as mqtt
import time
import json
BROKER = "mqttbroker.bc-pl.com"   # same as subscriber
PORT = 1883
USERNAME = "mqttuser"
PASSWORD = "Bfl@2025"

class DeviceCommandStateView(APIView):

    def post(self, request,id,tid):
        obj, created = DeviceCommandState.objects.update_or_create(
            device_id=id,
            defaults={"step":1,"task_id":tid}
        )
        print('id=',id)
        DEVICE_ID = id
        TOPIC = f"auto_feeder/{DEVICE_ID}/mode/switch"
        client = mqtt.Client(
        client_id=f"tasksubmit_{DEVICE_ID}_{int(time.time())}",
        protocol=mqtt.MQTTv311
        )

        def on_connect(client, userdata, flags, rc):
            print("Connected with rc:", rc)

        client.on_connect = on_connect
        if USERNAME and PASSWORD:
            client.username_pw_set(USERNAME, PASSWORD)

        client.loop_start()
        client.connect(BROKER, 1883, 60)
        # payload={"MODE": "AUTO"}

        client.publish(TOPIC,"AUTO", qos=1)
        time.sleep(1)

        client.loop_stop()
        client.disconnect()

        return Response({
            "status": "success",
            "message": "AUTO mode command sent",
            "payload": "AUTO"
        })


class DeviceCommandAbortView(APIView):

    def post(self, request,id,tid):
        DEVICE_ID = id
        TOPIC_Abort = f"auto_feeder/{DEVICE_ID}/auto/abort"
        client = mqtt.Client(
        client_id=f"tasksubmit_{DEVICE_ID}_{int(time.time())}",
        protocol=mqtt.MQTTv311
        )

        def on_connect(client, userdata, flags, rc):
            print("Connected with rc:", rc)

        client.on_connect = on_connect
        if USERNAME and PASSWORD:
            client.username_pw_set(USERNAME, PASSWORD)

        client.loop_start()
        client.connect(BROKER, 1883, 60)
        # payload={"MODE": "AUTO"}

        client.publish(TOPIC_Abort,"abort", qos=1)
        task = Task.objects.get(id=tid)
        task.status = "abort"
        task.save() 
        time.sleep(1)

        client.loop_stop()
        client.disconnect()
        
        return Response({
            "status": "success",
            "message": "Process Aborted"
        })
############################### log message ####################################
class AlertMessageView(APIView):
    def get(self,request,device_id):
        try:
            alert=Alert_message.objects.filter(device_id=device_id)[:7]
        except ObjectDoesNotExist:
            return Response({'message':"Alert Not found"},status=404)
        serializer=AlertMessageSerializer(alert,many=True)
        return Response(serializer.data,status=200)
############################### Task Clear #####################################
class TaskclearView(APIView):
    def post(self,request):
        serializer=TaskClearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device=serializer.validated_data['device']
        print(device)
        try:
            tasks = Task.objects.filter(device=device)
        except Task.DoesNotExist:
            return Response({"message":"Task NotFound.."})
        tasks.delete()
        return Response({"message":f"Tasks Related to {device} Deleted Successfully."},status=200)

