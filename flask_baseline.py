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
@app.route("/")
def home():
    return f"""
    <title>Weather for {obsName}</title>
    <h1>Weather for {obsName}</title>
    <p>Temperature : {tempK} Kelvin
    Relative Humidity : {humidity}
    Pressure : {presMB}
    Visibility : {visibilty}
    Sky Condition : {str(clouds)}
    Wind : {windDir} at {windSpeed} {windGust}</p>
"""

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



handler = ipinfo.getHandler(ipinfo_key)

details = handler.getDetails()

lat, lon = details.loc.split(',')

r = requests.get(f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}')
data = r.content.strip().decode('utf-8')

data = json.loads(data)

#print(data)
station = data['main']
tempK = station['temp']
feelsK = station['feels_like']
presMB = station['pressure']
humidity = station['humidity']
visibilty = data['visibility']
wind = data['wind']
windSpeed = wind['speed']
windDir = wind['deg']
windGust = wind['gust']
if (windGust - windSpeed) > 10:
    windGust = f'Gusting to {windGust}'
else:
    windGust = ''
clouds = data['clouds']
obsName = data['name']

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
