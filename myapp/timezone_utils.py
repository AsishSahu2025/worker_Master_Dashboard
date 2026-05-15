from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

def get_timezone_from_latlng(lat, lng):

    timezone_name = tf.timezone_at(
        lat=float(lat),
        lng=float(lng)
    )

    return timezone_name or "Asia/Kolkata"