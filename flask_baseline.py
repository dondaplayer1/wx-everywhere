import requests, ipinfo, json, os
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask, request, jsonify

cwd = Path(os.getcwd())
env_path = cwd / ".env"
load_dotenv(override=True)
load_dotenv(env_path)

app = Flask(__name__)

# Basic route

# Dynamic route with a variable converter
#@app.route("/user/<username>")
#def show_user(username):
#    return f"Hello, {username}!"

# Handling GET and POST requests (JSON API example)
#@app.route("/api/echo", methods=["POST"])
#def echo():
#    data = request.get_json()
#    return jsonify({"received": data}), 201

#api_key = '1261cbdbaf6003f3b570023a4bc68152'
api_key = os.getenv('OWM_KEY')
ipinfo_key = os.getenv('IPINFO_KEY')
'''
handler = ipinfo.getHandler(ipinfo_key)

details = handler.getDetails()

lat, lon = details.loc.split(',')
'''
#user_ip = request.remote_addr
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


day_forecast = {
    'units': None,
}

#the current conditions/obs
current = {
    'units': None,
    'temp': None,
    'feels': None,
    'pressure': None,
    'humidity': None,
    'visibility': None,
    'windSpeed': None,
    'windDir': None,
    'windGust': None,
    'cloudCover': None,
    'uvIndex': None
}

def get_current(lat, lon, units):
    r = requests.get(f'https://api.openweathermap.org/data/4.0/onecall/current?lat={lat}&lon={lon}&units={units}&appid={api_key}')
    data = r.content.strip().decode('utf-8')
    data = json.loads(data)
    current['units'] = units
    
    main = data['data'][0]
    current['temp'] = main['temp']
    current['feels'] = main['feels_like']
    current['pressure'] = main['pressure']
    current['humidity'] = main['humidity']
    current['visibility'] = main['visibility']
    current['windSpeed'] = main['wind_speed']
    current['windDir'] = main['wind_deg']
    current['windGust'] = main.get('wind_gust', None)
    current['cloudCover'] = main['clouds']
    current['uvIndex'] = main.get('uvi', None)
    return current

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
        

get_1day(43.5, -101.5, 'imperial')
print(day_forecast)
get_current(43.5, -101.5, 'imperial')
print(current)

'''
@app.route("/")
def home():
    user_ip = request.remote_addr
    country, lat, lon, city_name = get_location(user_ip)
    if country == 'US':
        default_units = 'imperial'
    else:
        default_units = 'metric'
    
    temp, feels, humidity, presMB, visibility, clouds, windDir, windSpeed, windGust = get_current(lat, lon, default_units)
    return(f"""
    <title>Weather for {city_name}</title>
    <h1>Weather for {city_name}</title>
    <p>Temperature : {temp}
    Feels like : {feels}
    Relative Humidity : {humidity}
    Pressure : {presMB}
    Visibility : {visibility}
    Sky Condition : {str(clouds)}
    Wind : {windDir} at {windSpeed} {windGust}</p> """) 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
'''