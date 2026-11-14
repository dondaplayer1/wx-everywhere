import requests, json, os, csv, re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, send_from_directory

cwd = Path(os.getcwd())
env_path = cwd / ".env"
load_dotenv(override=True)
load_dotenv(env_path)

# bootstrap lives in templates/css, so serve that folder at /css
app = Flask(__name__, static_folder='templates/css', static_url_path='/css')

api_key = os.getenv('OWM_KEY')


# load airport data
airports = {}
with open('data/airports.csv', newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['type'] in ('large_airport', 'medium_airport', 'small_airport'):
            place = (row['municipality'] or row['name'], row['latitude_deg'], row['longitude_deg'], row['iso_country'])
            if row['iata_code']:
                airports[row['iata_code'].upper()] = place  # AUS
            if row['icao_code']:
                airports[row['icao_code'].upper()] = place  # KAUS

# geolocation function
def get_location(ip_address):
    'returns country code, lat, lon, city name'
    try:
        response = requests.get("http://ip-api.com/json/{}".format(ip_address))
        js = response.json()
        country = js['countryCode']
        lat = js['lat']
        lon = js['lon']
        city = js['city']
        return country, lat, lon, city
    except Exception as e:
        return "Unknown"

default_units = 'metric' #metric (celsius and m/s), imperial (fahrenheit and mph), standard (kelvin (wtf lol) and m/s)

day_template = {
        'datetime': None,
        'sunrise': None,
        'sunset': None,
        'high': None,
        'low': None,
        'mornTemp': None,
        'dayTemp': None,
        'eveTemp': None,
        'nightTemp': None,
        'mornFeels': None,
        'dayFeels': None,
        'eveFeels': None,
        'nightFeels': None,
        'dewPoint': None,
        'humidity': None,
        'uvIndex': None,
        'pressure': None,
        'windSpeed': None,
        'windDir': None,
        'windGust': None,
        'cloudCover': None,
        'conditionMain': None,
        'conditionDesc': None,
        'conditionImageCode': None, #unsure how to build these
        'pop': None,
        'rainAmount': None, #these don't seem to be as values, rather some sort of percent?
        'snowAmount': None  #same here
    }

hourly_template = {
        'datetime': None,
        'temp': None,
        'feels': None,
        'dewPoint': None,
        'humidity': None,
        'uvIndex': None,
        'pressure': None,
        'windSpeed': None,
        'windDir': None,
        'windGust': None,
        'cloudCover': None,
        'conditionMain': None,
        'conditionDesc': None,
        'conditionImageCode': None, #unsure how to build these
        'pop': None,
        'rainAmount': None, #these don't seem to be as values, rather some sort of percent?
        'snowAmount': None  #same here
}

hourly_forecast = {
    'units': None,
}

day_forecast = {
    'units': None,
}

#the current conditions/obs
current = {
    'units': None,
    'datetime': None,       # for "Updated ..." on the page
    'tzOffset': None,       # seconds from UTC, so times show in the city's local time
    'temp': None,
    'feels': None,
    'dewPoint': None,
    'pressure': None,
    'humidity': None,
    'visibility': None,
    'windSpeed': None,
    'windDir': None,
    'windGust': None,
    'cloudCover': None,
    'uvIndex': None,
    'conditionMain': None,
    'conditionDesc': None
}

def get_current(lat, lon, units):
    r = requests.get(f'https://api.openweathermap.org/data/4.0/onecall/current?lat={lat}&lon={lon}&units={units}&appid={api_key}')
    data = r.content.strip().decode('utf-8')
    data = json.loads(data)
    current['units'] = units
    current['tzOffset'] = data.get('timezone_offset', 0)

    main = data['data'][0]
    weather = main['weather'][0]
    current['datetime'] = main['dt']
    current['temp'] = main['temp']
    current['feels'] = main['feels_like']
    current['dewPoint'] = main['dew_point']
    current['pressure'] = main['pressure']
    current['humidity'] = main['humidity']
    current['visibility'] = main.get('visibility', None)
    current['windSpeed'] = main['wind_speed']
    current['windDir'] = main['wind_deg']
    current['windGust'] = main.get('wind_gust', None)
    current['cloudCover'] = main['clouds']
    current['uvIndex'] = main.get('uvi', None)
    current['conditionMain'] = weather.get('main', None)
    current['conditionDesc'] = weather.get('description', None)
    return current

def get_1hour(lat, lon, units):
    r = requests.get(f'https://api.openweathermap.org/data/4.0/onecall/timeline/1h?lat={lat}&lon={lon}&units={units}&appid={api_key}')
    data = r.content.strip().decode('utf-8')
    data = json.loads(data)
    
    hourly_forecast['units'] = units
    for i in range(0, 18): #first 18 hours
        hour = hourly_template.copy()
        
        main = data['data'][i + 1] #adding 1 here so that it omits the hour 0 (which will be the current ob.) , but the hourly_forecast dictionary still starts at 0
        weather = main['weather'][0]
        
        hour['datetime'] = main['dt']
        hour['temp'] = main['temp']
        hour['feels'] = main['feels_like']
        hour['dewPoint'] = main['dew_point']
        hour['pressure'] = main['pressure']
        hour['humidity'] = main['humidity']
        hour['visibility'] = main['visibility']
        hour['windSpeed'] = main['wind_speed']
        hour['windDir'] = main['wind_deg']
        hour['windGust'] = main.get('wind_gust', None)
        hour['cloudCover'] = main['clouds']
        hour['uvIndex'] = main.get('uvi', None)
        hour['conditionMain'] = weather['main']
        hour['conditionDesc'] = weather['description']
        hour['pop'] = main.get('pop', 0)
        
        hourly_forecast[i] = hour
    return hourly_forecast
        
    

def get_1day(lat, lon, units): #daily forecasts
    r = requests.get(f'https://api.openweathermap.org/data/4.0/onecall/timeline/1day?lat={lat}&lon={lon}&units={units}&appid={api_key}')
    data = r.content.strip().decode('utf-8')
    data = json.loads(data)
    day_forecast['units'] = units
    for i in range(0,8):
        daily = day_template.copy()

        main = data['data'][i]
        temp = main['temp']
        feels = main['feels_like']
        weather = main['weather'][0]

        daily['datetime'] = main['dt']
        daily['sunrise'] = main['sunrise']
        daily['sunset'] = main['sunset']
        daily['high'] = temp['max']
        daily['low'] = temp['min']
        daily['mornTemp'] = temp['morn']
        daily['dayTemp'] = temp['day']
        daily['eveTemp'] = temp['eve']
        daily['nightTemp'] = temp['night']
        daily['mornFeels'] = feels['morn']
        daily['dayFeels'] = feels['day']
        daily['eveFeels'] = feels['eve']
        daily['nightFeels'] = feels['night']
        daily['dewPoint'] = main['dew_point']
        daily['humidity'] = main['humidity']
        daily['uvIndex'] = main.get('uvi', None) #do this way for ones that aren't in every day's forecast
        daily['pressure'] = main['pressure']
        daily['windSpeed'] = main['wind_speed']
        daily['windDir'] = main['wind_deg']
        daily['windGust'] = main.get('wind_gust', None)
        daily['cloudCover'] = main['clouds']
        daily['conditionMain'] = weather['main']
        daily['conditionDesc'] = weather['description']
        daily['pop'] = main['pop']

        day_forecast[i] = daily
    return day_forecast


#helper funcs
compass = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

def wind_dir(degrees):
    'converts direction in degrees to a compass dir'
    return compass[round(degrees / 22.5) % 16]

def local_time(timestamp, offset, fmt):
    'converts epoch to a cities local time'
    return datetime.fromtimestamp(timestamp, timezone(timedelta(seconds=offset))).strftime(fmt)

def is_old_browser():
    'True for browsers too old for bootstrap 5, like an iPhone 4 (iOS 7)'
    ua = request.headers.get('User-Agent', '')

    # iPhone/iPad/iPod say "iPhone OS 7_1_2"; bootstrap 5 needs iOS 10 or newer
    ios = re.search(r'(iPhone|iPad|iPod).* OS (\d+)_', ua)
    if ios:
        return int(ios.group(2)) < 10

    # old Android stock browsers say "Android 4.4"
    android = re.search(r'Android (\d+)', ua)
    if android:
        return int(android.group(1)) < 5

    # Internet Explorer, Opera Mini, old feature phones and BlackBerrys
    for name in ['MSIE ', 'Trident/', 'Opera Mini', 'MIDP', 'BlackBerry', 'BB10', 'Windows Phone', 'Symbian']:
        if name in ua:
            return True
    return False

def page(name):
    'picks templates/lite/<name> for old browsers, otherwise the normal template'
    if is_old_browser():
        return 'lite/' + name
    return name


# web pages
@app.route("/favicon.ico")
def favicon():
    # browsers ask for /favicon.ico on their own, so no <link> tag is needed in the templates
    return send_from_directory('assets', 'wx_everywhere.png', mimetype='image/png')


@app.route("/")
def index():
    return render_template(page('index.html'))

@app.route("/get/conditions")
def get_conditions():
    q = request.args.get('q', '').strip()

    # "locate me" button to geolocate the visitor
    if request.args.get('action') == 'locate':
        result = get_location(request.remote_addr)
        if result == "Unknown":
            return render_template(page('index.html'), error="Couldn't find your location. Try typing a city instead.")
        country, lat, lon, city_name = result

    # airport code, like MOP or KMOP
    elif q.upper() in airports:
        city_name, lat, lon, country = airports[q.upper()]

    # anything else, ask OpenWeatherMap geocode api (city name, "City, ST, US", "City, Country")
    else:
        r = requests.get('https://api.openweathermap.org/geo/1.0/direct', params={'q': q, 'limit': 1, 'appid': api_key})
        results = r.json()
        if not q or not isinstance(results, list) or len(results) == 0:
            return render_template(page('index.html'), error=f'No match for "{q}".', q=q)
        city_name = results[0]['name']
        lat = results[0]['lat']
        lon = results[0]['lon']
        country = results[0]['country']

    return redirect(url_for('conditions', lat=lat, lon=lon, name=city_name, country=country))


@app.route("/conditions")
def conditions():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    city_name = request.args.get('name', '')
    country = request.args.get('country', '')
    if not lat or not lon:
        return redirect(url_for('index'))

    if country == 'US':
        units = 'imperial'
        temp_unit, speed_unit = '°F', 'mph'
    else:
        units = default_units
        temp_unit, speed_unit = '°C', 'm/s'

    now = get_current(lat, lon, units)
    days = get_1day(lat, lon, units)
    hours = get_1hour(lat, lon, units)
    offset = now['tzOffset']

    wind_report = f"{wind_dir(now['windDir'])} at {round(now['windSpeed'])} {speed_unit}"
    if now['windGust']:
        wind_report += f", gusting to {round(now['windGust'])} {speed_unit}"

    # create day dict
    city_forecast = []
    for i in range(0, 7):
        day = days[i]
        city_forecast.append({
            'dayName': local_time(day['datetime'], 0, '%A'),  # forecast days are stamped midnight UTC, so read them in UTC
            'highT': f"{round(day['high'])}{temp_unit}",
            'lowT': f"{round(day['low'])}{temp_unit}",
            'wxType': day['conditionDesc'].capitalize(),
            'precip': round(day['pop'] * 100), #make this a percent
            'windDir': wind_dir(day['windDir']),
            'windSpeed': f"{round(day['windSpeed'])} {speed_unit}",
            'sunriseTime': local_time(day['sunrise'], offset, '%I:%M %p'), #create readable timestamp for sunrise
            'sunsetTime': local_time(day['sunset'], offset, '%I:%M %p'), #and sunset, from epoch
            'uvIndex': day['uvIndex'],
        })

    hourly_forecast = []
    for i in range(0, 18):
        hour = hours[i]
        time = local_time(hour['datetime'], 0, '%I %p')
        if time[0:1] == '0':
            time = time[1:]
        else:
            time = time
        temp = f"{round(hour['temp'])}{temp_unit}"
        feels = f"{round(hour['feels'])}{temp_unit}"
        windReport = f"{wind_dir(hour['windDir'])} at {round(hour['windSpeed'])} {speed_unit}"
        print(round(hour['pop'] * 100))
        if not abs(int(temp[:-2]) - int(feels[:-2])) <= 5:
            temp = f'{temp}, Feels Like {feels}'
        else:
            temp = temp
        hourly_forecast.append({
            'time': time,
            'temp': temp,
            'conditionMain': hour['conditionMain'].capitalize(),
            'windReport': windReport,
            'pops': round(hour['pop'] * 100),
            'remarks': f'UV Index; {round(hour['uvIndex'], 0)}'
        })

    return render_template(page('conditions.html'),
        cityName = city_name,
        tempF = f"{round(now['temp'])}{temp_unit}",
        feelsF = f"{round(now['feels'])}{temp_unit}",
        dewpoint = f"{round(now['dewPoint'])}{temp_unit}",
        wxDesc = now['conditionDesc'].capitalize(),
        relHum = now['humidity'],
        windReport = wind_report,
        pressure = f"{now['pressure']} mb",
        visibility = f"{now['visibility']} m" if now['visibility'] is not None else 'N/A', #error checking
        updateTime = local_time(now['datetime'], offset, '%a %I:%M %p'), #turn date into local time using helper
        cityForecast = city_forecast,
        hourlyForecast = hourly_forecast
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
