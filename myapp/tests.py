import redis
import psycopg2
from datetime import datetime ,timedelta
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Bot
import pytz
from myapp.models import Pond


# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Telegram bot token and group ID
TOKEN = '7822480011:AAELVUcySA8phvfHaj6G63QAhG_M8IoPM7g'  # Replace with your actual group ID
bot = Bot(token=TOKEN)
REDIS_HOST = "Vertoxlabs.redis.cache.windows.net"
REDIS_PASSWORD = "rdfFU7Y6aUS3Rnr4jubPQo4da6gi0ChSuAzCaAMJZoA="
REDIS_PORT = 6380

DATABASE_CONFIG = {
    'dbname': 'aquatest',
    'user': 'Vertoxlabs',
    'password': 'Vtx@2024',
    'host': 'aqua.postgres.database.azure.com',
    'port': 5432
}
# Create bot instance (without custom request class)
# bot = Bot(token=TOKEN)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, password=REDIS_PASSWORD, ssl=True)
def fetch_tasks_for_today():
    """Fetch tasks for today from Redis or database"""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = []

    # First, check Redis for today's tasks
    task_keys = r.keys(f"task:*")  # Assuming Redis stores tasks as "task:task_id"
    for key in task_keys:
        task_data = r.hgetall(key)  # Get task data as a hash
        task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}
        if task_data.get('date') == today:  # Check if the task's date matches today
            tasks.append(task_data)
    # If no tasks are found in Redis, fallback to the database
    if not tasks:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("""SELECT * FROM tasks WHERE date = %s""", [today])
        rows = cur.fetchall()
        for row in rows:
            tasks.append({
                'category_name': row[1],
                'date': row[2],
                'from_time': row[3],
                'to_time': row[4],
                'worker_name': row[5],
                'group_id': row[6],
                'task_id': row[7]
            })
        conn.close()

    return tasks

def send_daily_task_summary():
    """Send daily task summary at 6 AM"""
    tasks = fetch_tasks_for_today()
    if tasks:
        task_summary_message = "Good morning! Here are your tasks for today:\n\n"
        print(task_summary_message)
        for task in tasks:
            task_summary_message += f"Task: {task['category_name']}\n"
            task_summary_message += f"Worker: {task['worker_name']}\n"
            task_summary_message += f"pond: {task['pond_id']}\n"
            task_summary_message += f"Time: {task['from_time']} - {task['to_time']}\n\n"

        # Send the summary message to the group(s)
        # for task in tasks:
        print(f"Task Summary for {task['group_id']}")
        group_id = task['group_id']
        print(group_id)
        bot.send_message(chat_id=group_id, text=task_summary_message)
        print(f"Sent task summary to group {group_id}")
    else:
        print("No tasks found for today.")
        
def schedule_daily_task_summary():
    """Schedule daily task summary at 6 AM"""
    scheduler = BackgroundScheduler()

    # Define your time zone here (UTC, or your local time zone)
    timezone = pytz.timezone("Asia/Kolkata")  # Change this if necessary

    # Schedule the job for 6 AM in the defined time zone
    scheduler.add_job(
        send_daily_task_summary,
        CronTrigger(hour=15, minute=14, timezone=timezone)  # 6 AM daily in the specified time zone
    )
    scheduler.start()
    print("Scheduled daily task summary at 6 AM.")

def send_task_reminder(task):
    """Send a reminder message 10 minutes before the task starts"""
    task_reminder_message = f"Reminder: Your task '{task['category_name']}'  starts in 10 minutes!"
    group_id = task['group_id']
    bot.send_message(chat_id=group_id, text=task_reminder_message)
    print(f"Sent reminder for task {task['category_name']} to group {group_id}")

def schedule_task_reminders():
    """Schedule task reminders 10 minutes before task start time"""
    tasks = fetch_tasks_for_today()
    timezone = pytz.timezone("Asia/Kolkata")  # Set your desired time zone

    for task in tasks:
        # Parse the 'from_time' (assuming it's in a "HH:MM" format)
        from_time_str = task['from_time']
        from_time = datetime.strptime(from_time_str, "%H:%M")
        
        # Set the date to today, so we have a valid datetime object
        today = datetime.now(timezone).date()  # Get today's date
        from_time = datetime.combine(today, from_time.time())  # Combine today's date with the task's time

        print(f"Task '{task['category_name']}' from_time: {from_time}")

        # Get the time 10 minutes before the task starts
        reminder_time = from_time - timedelta(minutes=5)

        # Localize reminder time to the correct timezone
        reminder_time = timezone.localize(reminder_time)

        # Schedule the reminder
        scheduler = BackgroundScheduler()

        scheduler.add_job(
            send_task_reminder,
            DateTrigger(run_date=reminder_time, timezone=timezone),  # Trigger at reminder time
            args=[task]  # Pass the task to the function
        )
        scheduler.start()
        print(f"Scheduled reminder for task '{task['category_name']}' at {reminder_time}")


def main():
# Schedule the task for 6 AM daily
    # send_daily_task_summary()
    schedule_daily_task_summary()
    schedule_task_reminders()

    # Keep the script running
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        pass
        
if __name__ == "__main__":
    main()


        
# import rasterio
# import ee
# ee.Authenticate()
# ee.Initialize(project='ee-tapaskumarsahoo9090')
# # Define a region of interest (geometry)
# roi = ee.Geometry.Point([-74.0479, 40.6839])  # Example coordinates (New York City)

# # Define the time range for the image collection
# start_date = '2022-01-01'
# end_date = '2022-12-31'

# # Create a Sentinel-2 image collection filtered by location and date
# sentinel2_collection = (ee.ImageCollection('COPERNICUS/S2')
#                        .filterBounds(roi)
#                        .filterDate(ee.Date(start_date), ee.Date(end_date)))

# # Select bands of interest
# bands = ['B4', 'B3', 'B2']  # Red, Green, Blue

# # Create a function to apply to each image in the collection
# def addColor(image):
#     return image.select(bands).divide(10000)  # Scale the values to the range [0, 1]

# # Apply the function to each image in the collection
# sentinel2_collection = sentinel2_collection.map(addColor)

# # Get the first image in the collection
# image = sentinel2_collection.first()

# # Print the image information
# print('Image information:', image.getInfo())

# # Download the image
# task = ee.batch.Export.image.toDrive(image=image,
#                                      region=roi.getInfo()['coordinates'],
#                                      description='sentinel2_image',
#                                      folder='sentinel2_images',
#                                      scale=10,
#                                      maxPixels=1e13,
#                                      crs='EPSG:4326',
#                                      fileFormat='GeoTIFF',
#                                      formatOptions={'cloudOptimized': True},
#                                      skipEmptyTiles=True)

# task.start()



# from landsatxplore.api import API                                                                                  
# import pandas as pd
# import rasterio
# from rasterio.plot import show_hist
# import matplotlib.pyplot as plt
# import tifffile as tiff
# import tarfile
# username = "tapaskumarsahoo081@"
# password = "Bariflo@2023"
# api = API(username, password)
# scenes = api.search(
#     dataset='landsat_ot_c2_l2',
#     latitude=53.36305556,
#     longitude=-6.15583333,
#     start_date='2024-02-06',
#     end_date='2024-02-15',
#     max_cloud_cover=50
# )
# response = api.request(endpoint="dataset-catalogs")
# print(scenes)
 
# import rasterio
 
# # Given latitude and longitude                
# given_lat = 21.440603782181597
# given_lon = 86.46866649128583
# # Open the raster image
# with rasterio.open('C:/Users/tapaswebdev/Desktop/GIS/gis_project/gg.tif') as src:
#     # Get the affine transformation coefficients
#     transform = src.transform
 
#     # Get the dimensions of the raster image
#     width = src.width
#     height = src.height
 
#     # Initialize variables to store the nearest coordinate and its difference
#     nearest_coord = None
#     min_difference = float('inf')  # Initialize with a large value
 
#     # Iterate over all pixel coordinates
#     for y in range(height):
#         for x in range(width):
#             # Convert pixel coordinates to geographic coordinates
#             lon, lat = transform * (x, y)
#             # Calculate difference in latitude and longitude
#             lat_diff = abs(lat - given_lat)
#             lon_diff = abs(lon - given_lon)
#             # Calculate total difference (Euclidean distance)
#             total_diff = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
#             # Check if the current difference is smaller than the minimum difference found so far
#             if total_diff < min_difference:
#                 # Update nearest coordinate and minimum difference
#                 nearest_coord = (lat, lon)
#                 min_difference = total_diff
 
# # Print the nearest coordinate found
# print("Nearest Coordinate to ({}, {}) is at (Latitude: {}, Longitude: {})".format(given_lat, given_lon, nearest_coord[0], nearest_coord[1]))




# import pandas as pd
# import ee
 
# ee.Authenticate()
# ee.Initialize(project='ee-tapaskumarsahoo9090')
 
# # Define the geometry
# lat = 19.813744
# long = 85.824953
# geometry = ee.Geometry.Point([long, lat])
# # d_OLI = ee.Image.constant(img.get('EARTH_SUN_DISTANCE'))
# # Load the Sentinel 2 image
# image = ee.ImageCollection("COPERNICUS/S2_SR") \
#             .filterBounds(geometry) \
#             .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 20)) \
#             .first()
 
# # Calculate pH
# ph = ee.Image(8.339).subtract(ee.Image(0.827).multiply(image.select('B1').divide(image.select('B8')))).rename('pH')
# # Calculate Dissolved Oxygen
# dissolved_oxygen = ee.Image(-0.0167).multiply(image.select('B8')) \
#                     .add(ee.Image(0.0067).multiply(image.select('B9'))) \
#                     .add(ee.Image(0.0083).multiply(image.select('B11'))) \
#                     .add(ee.Image(9.577)).rename('Dissolved_Oxygen')
 
# # Calculate NDVI (Normalized Difference Vegetation Index)
# ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
 
# # Calculate NDTI (Normalized Difference Turbidity Index)
# ndti = image.normalizedDifference(['B4', 'B3']).rename('NDTI')
 
# # Calculate GCI (Green Chlorophyll Index)
# gci = image.select('B3').pow(0.5).multiply(image.select('B4')).pow(0.5).subtract(1).rename('GCI')
 
# # Calculate NDCI (Normalized Difference Chlorophyll Index)
# ndci = (image.select('B5').subtract(image.select('B4'))).divide(image.select('B5').add(image.select('B4'))).rename('NDCI')
 
# # Calculate NDWI (Normalized Difference Water Index)
# ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
 
# # Calculate Total Suspended Solids (TSS)
# tss = image.select('B4').subtract(image.select('B8')).pow(2).multiply(0.6113).rename('TSS')
 
# # Calculate CDOM index
# cdom_index = image.select('B3').divide(image.select('B2')).rename('CDOM_Index')
 
# # Reduce the images to get the mean values
# ph_mean = ph.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('pH')
# dissolved_oxygen_mean = dissolved_oxygen.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('Dissolved_Oxygen')
# ndvi_mean = ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('NDVI')
# ndti_mean = ndti.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('NDTI')
# gci_mean = gci.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('GCI')
# ndci_mean = ndci.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('NDCI')
# ndwi_mean = ndwi.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('NDWI')
# tss_mean = tss.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('TSS')
# cdom_mean = cdom_index.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=10).get('CDOM_Index')
 
# # Create a dictionary to store the data
# data = {
#     'pH': ph_mean.getInfo(),
#     'Dissolved Oxygen': dissolved_oxygen_mean.getInfo(),
#     'NDVI': ndvi_mean.getInfo(),
#     'NDTI': ndti_mean.getInfo(),
#     'GCI': gci_mean.getInfo(),
#     'NDCI': ndci_mean.getInfo(),
#     'NDWI': ndwi_mean.getInfo(),
#     'TSS': tss_mean.getInfo(),
#     'CDOM':cdom_mean.getInfo(),
#     'AQUATIC_MACROPYTES':ndvi_mean.getInfo(),
# }
 
# # Create a pandas DataFrame
# df = pd.DataFrame(data, index=[0])
 
# # Save DataFrame to CSV file
# df.to_csv('water_quality_data.csv', index=False)
 
# print("Data saved successfully.")

# point_str = "SRID=4326;POINT (21.46989235256186 85.83305171845856)"
# # gh = point_str.split("(")[1].split(")")[0]

# # coordinates = point_str.split("(")[1].split(")")[0]                   # Split the string to extract coordinates
# # print(coordinates)
# # latitude, longitude = map(float, coordinates.split())           # Split the coordinates into latitude and longitude
# # print("Latitude:", latitude)
# # print("Longitude:", longitude)

# coordinates = point_str.strip("()").split(",")
# latitude, longitude = map(float, coordinates)
# print(latitude)


# nums = [3,4,6,2]
# def square(n):
#     return n*n
# mapped = list(map(square,nums))
# print(mapped)
# print(type(mapped))


# marks = [77,97,64,85,55]
# def grade(marks):
#     if marks >= 90:
#         return 'A'
#     elif 80 <= marks < 90:
#         return 'B'
#     elif 70 <= marks < 80:
#         return 'C'
#     elif 60 <= marks < 70:
#         return 'D'
#     else:
#         return 'F'
# grad = list(map(grade,marks))
# print("Exam",marks)
# # print("Grade",next(grad))
# # print("Grade",next(grad))
# # print("Grade",list(grad))
# print("Grade",grad)


# a = [10,20,30,40,50]
# def inc(n):
#     return n+2
# result = list(map(inc, a))
# print(result)


# a = [12,23,34,45,78]
# def res(n):
#     return n*n
# result = list(map(res, a))
# print(result)

# ************************************************************************************

# from shapely.geometry import Point, Polygon
# polygon_coords = [(20.18297539978675, 85.6270230268892),
#                   (20.1820535432657, 85.62676553742786),
#                   (20.18191753118631, 85.62739853235374),
#                   (20.18276886410021, 85.62759164944977),
#                   (20.18297539978675, 85.6270230268892)]

# # Create a Shapely Polygon object
# polygon = Polygon(polygon_coords)

# # Define a point to test
# test_point = Point(20.1825, 85.6272)  # Example point, replace with your point coordinates

# # Check if the point is inside the polygon
# is_inside = test_point.within(polygon)

# print(is_inside)

# ************************************************************************************



import ee
from google.oauth2 import service_account
# Define the required scopes
SCOPES = ['https://www.googleapis.com/auth/earthengine.readonly']
# Load the credentials from the JSON key file
credentials = service_account.Credentials.from_service_account_file(
    'ee-tapaskumarsahoo9090-6245e11643e0.json', scopes=SCOPES)                      #for local machine uncomment this line.
    # '/app/ee-tapaskumarsahoo9090-6245e11643e0.json', scopes=SCOPES)               #for docker file uncomment this line.
    
# Initialize the Earth Engine with the credentials
ee.Initialize(credentials)

 
geometry = ee.Geometry.Polygon([[[30.76171875, 0.9049611504960419],
          [30.8935546875, -3.487377195492663],
          [35.5517578125, -3.2680324702882952],
          [35.5517578125, 1.9593043032313748]]])
 

# begin date
iniDate = '2015-05-01'
# end date
endDate = '2018-03-31'
# (5) Adjust a cloud % threshold here:
cloudPerc = 5

#########################################################/
# Map.centerObject(geometry, 7)
 
# Import Collections #
 
# sentinel-2
MSI = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
 
# landsat-8 surface reflactance product (for masking purposes)
SRP = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
 
# toms / omi
ozone = ee.ImageCollection('TOMS/MERGED')
 
#########################################################/
#########################################################/
#########################################################/
 
pi = ee.Image(3.141592)
 
# water mask
startMonth = 5
endMonth = 9
startYear = 2013
endYear = 2017
 
forMask = SRP.filterBounds(geometry).select('B6').filterMetadata('CLOUD_COVER', "less_than", 10).filter(
    ee.Filter.calendarRange(startMonth, endMonth, 'month')).filter(ee.Filter.calendarRange(startYear, endYear, 'year'))
mask = ee.Image(forMask.select('B6').median().lt(300))
mask = mask.updateMask(mask)
 
# filter sentinel 2 collection
FC = MSI.filterDate(iniDate, endDate).filterBounds(geometry).filterMetadata('CLOUDY_PIXEL_PERCENTAGE', "less_than",
                                                                            cloudPerc)
 
 
# #########################################################/
# #########################################################/
# #########################################################/
# Mapping functions #
 
def s2Correction(img):
    # msi bands
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
 
    # rescale
    rescale = img.select(bands).divide(10000).multiply(mask)
 
    # tile footprint
    footprint = rescale.geometry()
 
    # dem
    DEM = ee.Image('USGS/SRTMGL1_003').clip(footprint)
 
    # ozone
    DU = ee.Image(ozone.filterDate(iniDate, endDate).filterBounds(footprint).mean())
 
    # Julian Day
    imgDate = ee.Date(img.get('system:time_start'))
    FOY = ee.Date.fromYMD(imgDate.get('year'), 1, 1)
    JD = imgDate.difference(FOY, 'day').int().add(1)
 
    # earth-sun distance
    myCos = ((ee.Image(0.0172).multiply(ee.Image(JD).subtract(ee.Image(2)))).cos()).pow(2)
    cosd = myCos.multiply(pi.divide(ee.Image(180))).cos()
    d = ee.Image(1).subtract(ee.Image(0.01673)).multiply(cosd).clip(footprint)
 
    # sun azimuth
    SunAz = ee.Image.constant(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')).clip(footprint)
 
    # sun zenith
    SunZe = ee.Image.constant(img.get('MEAN_SOLAR_ZENITH_ANGLE')).clip(footprint)
    cosdSunZe = SunZe.multiply(pi.divide(ee.Image(180))).cos()  # in degrees
    sindSunZe = SunZe.multiply(pi.divide(ee.Image(180))).sin()  # in degrees
 
    # sat zenith
    SatZe = ee.Image.constant(img.get('MEAN_INCIDENCE_ZENITH_ANGLE_B5')).clip(footprint)
    cosdSatZe = (SatZe).multiply(pi.divide(ee.Image(180))).cos()
    sindSatZe = (SatZe).multiply(pi.divide(ee.Image(180))).sin()
 
    # sat azimuth
    SatAz = ee.Image.constant(img.get('MEAN_INCIDENCE_AZIMUTH_ANGLE_B5')).clip(footprint)
 
    # relative azimuth
    RelAz = SatAz.subtract(SunAz)
    cosdRelAz = RelAz.multiply(pi.divide(ee.Image(180))).cos()
 
    # Pressure
    P = (ee.Image(101325).multiply(ee.Image(1).subtract(ee.Image(0.0000225577).multiply(DEM)).pow(5.25588)).multiply(
        0.01)).multiply(mask)
    Po = ee.Image(1013.25)
 
    # esun
    ESUN = ee.Image(ee.Array([ee.Image(img.get('SOLAR_IRRADIANCE_B1')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B2')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B3')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B4')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B5')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B6')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B7')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B8')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B8A')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B11')),
                              ee.Image(img.get('SOLAR_IRRADIANCE_B2'))]
                             )).toArray().toArray(1)
 
    ESUN = ESUN.multiply(ee.Image(1))
 
    ESUNImg = ESUN.arrayProject([0]).arrayFlatten([bands])
 
    # create empty array for the images
    imgArr = rescale.select(bands).toArray().toArray(1)
 
    # pTOA to Ltoa
    Ltoa = imgArr.multiply(ESUN).multiply(cosdSunZe).divide(pi.multiply(d.pow(2)))
 
    # band centers
    bandCenter = ee.Image(443).divide(1000).addBands(ee.Image(490).divide(1000)) \
        .addBands(ee.Image(560).divide(1000)) \
        .addBands(ee.Image(665).divide(1000)) \
        .addBands(ee.Image(705).divide(1000)) \
        .addBands(ee.Image(740).divide(1000)) \
        .addBands(ee.Image(783).divide(1000)) \
        .addBands(ee.Image(842).divide(1000)) \
        .addBands(ee.Image(865).divide(1000)) \
        .addBands(ee.Image(1610).divide(1000)) \
        .addBands(ee.Image(2190).divide(1000)) \
        .toArray().toArray(1)
 
    # ozone coefficients
    koz = ee.Image(0.0039).addBands(ee.Image(0.0213)) \
        .addBands(ee.Image(0.1052)) \
        .addBands(ee.Image(0.0505)) \
        .addBands(ee.Image(0.0205)) \
        .addBands(ee.Image(0.0112)) \
        .addBands(ee.Image(0.0075)) \
        .addBands(ee.Image(0.0021)) \
        .addBands(ee.Image(0.0019)) \
        .addBands(ee.Image(0)) \
        .addBands(ee.Image(0)) \
        .toArray().toArray(1)
 
    # Calculate ozone optical thickness
    Toz = koz.multiply(DU).divide(ee.Image(1000))
 
    # Calculate TOA radiance in the absense of ozone
    Lt = Ltoa.multiply(((Toz)).multiply((ee.Image(1).divide(cosdSunZe)).add(ee.Image(1).divide(cosdSatZe))).exp())
 
    # Rayleigh optical thickness
    Tr = (P.divide(Po)).multiply(ee.Image(0.008569).multiply(bandCenter.pow(-4))).multiply((ee.Image(1).add(
        ee.Image(0.0113).multiply(bandCenter.pow(-2))).add(ee.Image(0.00013).multiply(bandCenter.pow(-4)))))
 
    # Specular reflection (s- and p- polarization states)
    theta_V = ee.Image(0.0000000001)
    sin_theta_j = sindSunZe.divide(ee.Image(1.333))
 
    theta_j = sin_theta_j.asin().multiply(ee.Image(180).divide(pi))
 
    theta_SZ = SunZe
 
    R_theta_SZ_s = (
        ((theta_SZ.multiply(pi.divide(ee.Image(180)))).subtract(theta_j.multiply(pi.divide(ee.Image(180))))).sin().pow(
            2)).divide(
        (((theta_SZ.multiply(pi.divide(ee.Image(180)))).add(theta_j.multiply(pi.divide(ee.Image(180))))).sin().pow(2)))
 
    R_theta_V_s = ee.Image(0.0000000001)
 
    R_theta_SZ_p = (
        ((theta_SZ.multiply(pi.divide(180))).subtract(theta_j.multiply(pi.divide(180)))).tan().pow(2)).divide(
        (((theta_SZ.multiply(pi.divide(180))).add(theta_j.multiply(pi.divide(180)))).tan().pow(2)))
 
    R_theta_V_p = ee.Image(0.0000000001)
 
    R_theta_SZ = ee.Image(0.5).multiply(R_theta_SZ_s.add(R_theta_SZ_p))
 
    R_theta_V = ee.Image(0.5).multiply(R_theta_V_s.add(R_theta_V_p))
 
    # Sun-sensor geometry
    theta_neg = ((cosdSunZe.multiply(ee.Image(-1))).multiply(cosdSatZe)).subtract(
        (sindSunZe).multiply(sindSatZe).multiply(cosdRelAz))
 
    theta_neg_inv = theta_neg.acos().multiply(ee.Image(180).divide(pi))
 
    theta_pos = (cosdSunZe.multiply(cosdSatZe)).subtract(sindSunZe.multiply(sindSatZe).multiply(cosdRelAz))
 
    theta_pos_inv = theta_pos.acos().multiply(ee.Image(180).divide(pi))
 
    cosd_tni = theta_neg_inv.multiply(pi.divide(180)).cos()  # in degrees
 
    cosd_tpi = theta_pos_inv.multiply(pi.divide(180)).cos()  # in degrees
 
    Pr_neg = ee.Image(0.75).multiply((ee.Image(1).add(cosd_tni.pow(2))))
 
    Pr_pos = ee.Image(0.75).multiply((ee.Image(1).add(cosd_tpi.pow(2))))
 
    # Rayleigh scattering phase function
    Pr = Pr_neg.add((R_theta_SZ.add(R_theta_V)).multiply(Pr_pos))
 
    # rayleigh radiance contribution
    denom = ee.Image(4).multiply(pi).multiply(cosdSatZe)
    Lr = (ESUN.multiply(Tr)).multiply(Pr.divide(denom))
 
    # rayleigh corrected radiance
    Lrc = Lt.subtract(Lr)
    LrcImg = Lrc.arrayProject([0]).arrayFlatten([bands])
 
    # Aerosol Correction #
 
    # Bands in nm
    bands_nm = ee.Image(443).addBands(ee.Image(490)) \
        .addBands(ee.Image(560)) \
        .addBands(ee.Image(665)) \
        .addBands(ee.Image(705)) \
        .addBands(ee.Image(740)) \
        .addBands(ee.Image(783)) \
        .addBands(ee.Image(842)) \
        .addBands(ee.Image(865)) \
        .addBands(ee.Image(0)) \
        .addBands(ee.Image(0)) \
        .toArray().toArray(1)
 
    # Lam in SWIR bands
    Lam_10 = LrcImg.select('B11')
    Lam_11 = LrcImg.select('B12')
 
    # Calculate aerosol type
    eps = (
        (((Lam_11).divide(ESUNImg.select('B12'))).log()).subtract(
            ((Lam_10).divide(ESUNImg.select('B11'))).log())).divide(
        ee.Image(2190).subtract(ee.Image(1610)))
 
    # Calculate multiple scattering of aerosols for each band
    Lam = (Lam_11).multiply(((ESUN).divide(ESUNImg.select('B12')))).multiply(
        (eps.multiply(ee.Image(-1))).multiply((bands_nm.divide(ee.Image(2190)))).exp())
 
    # diffuse transmittance
    trans = Tr.multiply(ee.Image(-1)).divide(ee.Image(2)).multiply(ee.Image(1).divide(cosdSatZe)).exp()
 
    # Compute water-leaving radiance
    Lw = Lrc.subtract(Lam).divide(trans)
 
    # water-leaving reflectance
    pw = (Lw.multiply(pi).multiply(d.pow(2)).divide(ESUN.multiply(cosdSunZe)))
 
    # remote sensing reflectance
    Rrs_coll = (pw.divide(pi).arrayProject([0]).arrayFlatten([bands]).slice(0, 9))
 
    return (Rrs_coll.set('system:time_start', img.get('system:time_start')))
 
 
def chlorophyll(img):
    NDCI_coll = (img.select('B5').subtract(img.select('B4'))).divide(img.select('B5').add(img.select('B4')))
    chlor_a_coll = ee.Image(14.039).add(ee.Image(86.115).multiply(NDCI_coll)).add(
        ee.Image(194.325).multiply(NDCI_coll.pow(ee.Image(2))))
    return (chlor_a_coll.updateMask(chlor_a_coll.lt(100)).set('system:time_start', img.get('system:time_start')))
 
 
def secchi(img):
 
    blueRed_coll = (img.select('B2').divide(img.select('B4'))).log()
    lnMOSD_coll = (ee.Image(1.4856).multiply(blueRed_coll)).add(
        ee.Image(0.2734))  # R2 = 0.8748 with Anthony's in-situ data
    MOSD_coll = ee.Image(10).pow(lnMOSD_coll)
    sd_coll = (ee.Image(0.1777).multiply(MOSD_coll)).add(ee.Image(1.0813))
    return (sd_coll.updateMask(sd_coll.lt(10)).set('system:time_start', img.get('system:time_start')))
 
 
def trophicState(img):
    tsi_coll = ee.Image(30.6).add(ee.Image(9.81).multiply(img.log()))
    return (tsi_coll.updateMask(tsi_coll.lt(200)).set('system:time_start', img.get('system:time_start')))
 
 
def reclassify(img):
    # Create conditions
    mask1 = img.lt(30)  # (1)
    mask2 = img.gte(30).And(img.lt(40))  # (2)
    mask3 = img.gte(40).And(img.lt(50))  # (3)
    mask4 = img.gte(50).And(img.lt(60))  # (4)
    mask5 = img.gte(60).And(img.lt(70))  # (5)
    mask6 = img.gte(70).And(img.lt(80))  # (6)
    mask7 = img.gte(80)  # (7)
 
    # Reclassify conditions into new values
    img1 = img.where(mask1.eq(1), 1).mask(mask1)
    img2 = img.where(mask2.eq(1), 2).mask(mask2)
    img3 = img.where(mask3.eq(1), 3).mask(mask3)
    img4 = img.where(mask4.eq(1), 4).mask(mask4)
    img5 = img.where(mask5.eq(1), 5).mask(mask5)
    img6 = img.where(mask6.eq(1), 6).mask(mask6)
    img7 = img.where(mask7.eq(1), 7).mask(mask7)
 
    # Ouput of reclassified image
    tsi_collR = img1.unmask(img2).unmask(img3).unmask(img4).unmask(img5).unmask(img6).unmask(img7)
    return (tsi_collR.updateMask(tsi_collR.set('system:time_start', img.get('system:time_start'))))
 
 
#########################################################/
#########################################################/
#########################################################/
# Collection Processing #
 
# atmospheric correction
Rrs_coll = FC.map(s2Correction)
 
# chlorophyll-a
chlor_a_coll = Rrs_coll.map(chlorophyll)
 
# sd
sd_coll = Rrs_coll.map(secchi)
 
# tsi
tsi_coll = chlor_a_coll.map(trophicState)
 
# tsi reclass
tsi_collR = tsi_coll.map(reclassify)
 
Rsr = Rrs_coll.mean()
Rsr_vis = {'min': 0, 'max': 0.03, 'bands': 'B4,B3,B2'}
Rsr_mapid = Rsr.getMapId(Rsr_vis)
 
SD = sd_coll.mean()
SD_vis = {'min': 0, 'max': 2, 'palette': '#800000,#FF9700,#7BFF7B,#0080FF,#000080'}
SD_mapid = SD.getMapId(SD_vis)
 
TSI = tsi_coll.mean()
TSI_vis = {'min': 30, 'max': 80,'palette':'darkblue,blue,cyan,limegreen,yellow,orange,orangered,darkred'}
TSI_mapid = TSI.getMapId(TSI_vis)
 
TSI_R = tsi_collR.mean()
TSI_R_vis = {'min': 1, 'max': 7, 'palette': 'purple,blue,limegreen,yellow,orange,orangered,darkred'}
TSI_R_mapid = TSI_R.getMapId(TSI_R_vis)
 
print('RSR',Rsr_mapid)
print('SD',SD_mapid)
print('TSI',TSI_mapid)
print('TSI R',TSI_R_mapid)
 
# #########################################################/
# #########################################################/
# #########################################################/
# Map Layers #
# Map.addLayer(mask, {}, 'mask', false)
# Map.addLayer(Rrs_coll.mean(), {min: 0, max: 0.03, bands: ['B4', 'B3', 'B2']}, 'Mean RGB', false)
# Map.addLayer(chlor_a_coll.mean(), {min: 0, max: 40,
#                                    palette: ['darkblue', 'blue', 'cyan', 'limegreen', 'yellow', 'orange', 'orangered',
#                                              'darkred']}, 'Mean chlor-a', false)
# Map.addLayer(sd_coll.mean(), {min: 0, max: 2, palette: ['800000', 'FF9700', '7BFF7B', '0080FF', '000080']}, 'Mean Zsd',
#              false)
# Map.addLayer(tsi_coll.mean(), {min: 30, max: 80,
#                                palette: ['darkblue', 'blue', 'cyan', 'limegreen', 'yellow', 'orange', 'orangered',
#                                          'darkred']}, 'Mean TSI', false)
# Map.addLayer(tsi_collR.mode(),
#              {min: 1, max: 7, palette: ['purple', 'blue', 'limegreen', 'yellow', 'orange', 'orangered', 'darkred']},
#              'Mode TSI Class', true)
 
#########################################################/
#########################################################/
#########################################################/
# Time Series #
 
# # Chlorophyll-a time series
# chlorTimeSeries = ui.Chart.image.seriesByRegion(
# chlor_a_coll, geometry, ee.Reducer.mean())
# .setChartType('ScatterChart')
#     .setOptions({
#     title: 'Mean Chlorphyll-a',
#     vAxis: {title: 'Chlor-a [micrograms/L]'},
#     lineWidth: 1,
#     pointSize: 4,
# })
#
# # SD time series
# sdTimeSeries = ui.Chart.image.seriesByRegion(
# sd_coll, geometry, ee.Reducer.mean())
# .setChartType('ScatterChart')
#     .setOptions({
#     title: 'Mean Secchi Depth',
#     vAxis: {title: 'Zsd [m]'},
#     lineWidth: 1,
#     pointSize: 4,
# })
#
# # TSI time series
# tsiTimeSeries = ui.Chart.image.seriesByRegion(
# tsi_coll, geometry, ee.Reducer.mean())
# .setChartType('ScatterChart')
#     .setOptions({
#     title: 'Mean Trophic State Index',
#     vAxis: {title: 'TSI [1-100]'},
#     lineWidth: 1,
#     pointSize: 4,
# })
#
# # TSI Reclass time series
# tsiRTimeSeries = ui.Chart.image.seriesByRegion(
# tsi_collR, geometry, ee.Reducer.mode())
# .setChartType('ScatterChart')
#     .setOptions({
#     title: 'Mode Trophic State Index Class',
#     vAxis: {title: 'TSI Class'},
#     lineWidth: 1,
#     pointSize: 4,
# })
#
# print(chlorTimeSeries)
# print(sdTimeSeries)
# print(tsiTimeSeries)
# print(tsiRTimeSeries)

@csrf_exempt
def demo(request):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)
        name = jsondata.get('name')
        latitude = jsondata.get('latitude')
        longitude = jsondata.get('longitude')
        polygon_points  = jsondata.get('location')
        clusterid  = jsondata.get('clusterid')
        area = jsondata.get('area')
        city = jsondata.get('city')
        telegram_group_id = jsondata.get('telegram_group_id')

        
        try:
            register_intstance = Cluster.objects.get(id=clusterid)
            if register_intstance:
                points_str = ', '.join([f'{point[0]} {point[1]}' for point in polygon_points])
        
                points_str += f', {polygon_points[0][0]} {polygon_points[0][1]}'
                print(f'SRID=4326;POLYGON({points_str})')

                latitude_str = str(latitude)
                longitude_str = str(longitude)
                xx = Pond(name=name,city=city,registration=register_intstance,area=area,telegram_group_id=telegram_group_id)                                                                                                                                                                                                                                                                                                                
                xx.location = f'POLYGON(({points_str}))'
                xx.latlong = f'({latitude_str},{longitude_str})'
                xx.save()

                return JsonResponse({'message': 'Location saved successfully.'})
        except Exception as e:
            return JsonResponse({'message': 'Location not saved'})