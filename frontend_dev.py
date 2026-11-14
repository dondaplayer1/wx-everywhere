"""
WeatherEverywhere - frontend dev server.

Routes:
  /                 landing page (search box + "Locate me" / "Submit")
  /get/conditions   resolves the user's input (or their IP) to lat/lon, then redirects to /conditions
  /conditions       renders conditions.html for ?lat=&lon=&name=

Set USE_SAMPLE_DATA=1 (the default when OWM_KEY is missing) to render from sample_data/*.json
without touching any external API.
"""
import csv, json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env", override=True)

OWM_KEY = os.getenv("OWM_KEY")
IPINFO_KEY = os.getenv("IPINFO_KEY")
USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "1" if not OWM_KEY else "0") == "1"
SAMPLE_DIR = BASE / "sample_data"
HTTP_TIMEOUT = 10

# Bootstrap lives in templates/css; serve it at /css/bootstrap.min.css
app = Flask(__name__, static_folder="templates/css", static_url_path="/css")

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR",
}
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


class LookupError_(Exception):
    """User-facing lookup failure; message is shown on the landing page."""


# --------------------------------------------------------------------------- airports
def _load_airports():
    """Optional: data/airports.csv from https://ourairports.com/data/ (public domain).
    Maps IATA (AUS) and ICAO/ident (KAUS) codes -> (name, lat, lon)."""
    path = BASE / "data" / "airports.csv"
    table = {}
    if not path.exists():
        return table
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] not in ("large_airport", "medium_airport", "small_airport"):
                continue
            entry = (row["municipality"] or row["name"], float(row["latitude_deg"]), float(row["longitude_deg"]))
            table.setdefault(row["ident"].upper(), entry)
            if row.get("iata_code"):
                table.setdefault(row["iata_code"].upper(), entry)
    return table


AIRPORTS = _load_airports()


# --------------------------------------------------------------------------- lookups
def geolocate(ip):
    """IP -> (name, lat, lon) via ipinfo. Must be passed the *client's* IP;
    calling ipinfo with no IP returns the server's own location."""
    if USE_SAMPLE_DATA:
        return "Austin, Texas, US", 30.2672, -97.7431
    import ipinfo
    details = ipinfo.getHandler(IPINFO_KEY).getDetails(ip)
    loc = getattr(details, "loc", None)
    if not loc:  # private/LAN IPs (127.0.0.1, 192.168.x.x) have no location
        raise LookupError_("Couldn't locate you from your connection. Try typing a city instead.")
    lat, lon = (float(x) for x in loc.split(","))
    name = ", ".join(p for p in (getattr(details, "city", None), getattr(details, "region", None),
                                 getattr(details, "country", None)) if p)
    return name, lat, lon


def geocode(query):
    """Free-text location -> (name, lat, lon).
    Order: airport code table -> US ZIP -> OWM direct geocoding (worldwide city search)."""
    q = query.strip()
    if not q:
        raise LookupError_("Type a location, or use Locate me.")

    code = q.upper()
    if re.fullmatch(r"[A-Z0-9]{3,4}", code) and code in AIRPORTS:
        return AIRPORTS[code]

    if USE_SAMPLE_DATA:
        hit = json.loads((SAMPLE_DIR / "geocode_austin.json").read_text())[0]
        return _place_name(hit), hit["lat"], hit["lon"]

    if re.fullmatch(r"\d{5}", q):  # US ZIP; for other countries use /geo/1.0/zip?zip=CODE,CC
        r = requests.get("https://api.openweathermap.org/geo/1.0/zip",
                         params={"zip": f"{q},US", "appid": OWM_KEY}, timeout=HTTP_TIMEOUT)
        if r.ok:
            hit = r.json()
            return f"{hit['name']}, US", hit["lat"], hit["lon"]

    # OWM wants "city,state,country"; "Austin, TX" would otherwise be read as country "TX".
    parts = [p.strip() for p in q.split(",") if p.strip()]
    if len(parts) == 2 and parts[1].upper() in US_STATES:
        parts.append("US")
    r = requests.get("https://api.openweathermap.org/geo/1.0/direct",
                     params={"q": ",".join(parts), "limit": 1, "appid": OWM_KEY}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    hits = r.json()
    if not hits:
        raise LookupError_(f'No match for "{q}". Try "City, Country" or an airport code.')
    hit = hits[0]
    return _place_name(hit), hit["lat"], hit["lon"]


def _place_name(hit):
    return ", ".join(p for p in (hit.get("name"), hit.get("state"), hit.get("country")) if p)


def fetch_onecall(lat, lon):
    """Current + daily forecast in one request (One Call 3.0, imperial units)."""
    if USE_SAMPLE_DATA:
        return json.loads((SAMPLE_DIR / "onecall_austin.json").read_text())
    r = requests.get("https://api.openweathermap.org/data/3.0/onecall",
                     params={"lat": lat, "lon": lon, "units": "imperial",
                             "exclude": "minutely,hourly,alerts", "appid": OWM_KEY},
                     timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------- formatting
def compass(deg):
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def local_time(ts, tz, fmt="%-I:%M %p"):
    return datetime.fromtimestamp(ts, tz).strftime(fmt)


def build_context(data, name):
    """Map One Call JSON onto the variables conditions.html expects."""
    tz = timezone(timedelta(seconds=data.get("timezone_offset", 0)))
    cur = data["current"]

    wind = f"{compass(cur['wind_deg'])} {round(cur['wind_speed'])} mph"
    gust = cur.get("wind_gust")
    if gust and gust - cur["wind_speed"] >= 10:
        wind += f", gusts {round(gust)} mph"

    forecast = []
    for d in data.get("daily", [])[:7]:
        forecast.append({
            "dayName": local_time(d["dt"], tz, "%A"),
            "highT": f"{round(d['temp']['max'])}°",
            "lowT": f"{round(d['temp']['min'])}°",
            "wxType": d["weather"][0]["description"].capitalize(),
            "precip": round(d.get("pop", 0) * 100),
            "windDir": compass(d["wind_deg"]),
            "windSpeed": f"{round(d['wind_speed'])} mph",
            "sunriseTime": local_time(d["sunrise"], tz),
            "sunsetTime": local_time(d["sunset"], tz),
            "uvIndex": round(d.get("uvi", 0)),
        })

    vis_m = cur.get("visibility")
    return {
        "cityName": name,
        "tempF": f"{round(cur['temp'])}°F",
        "feelsF": f"{round(cur['feels_like'])}°F",
        "wxDesc": cur["weather"][0]["description"].capitalize(),
        "relHum": cur["humidity"],
        "windReport": wind,
        "pressure": f"{cur['pressure'] * 0.02953:.2f} inHg ({cur['pressure']} mb)",
        "visibility": f"{vis_m / 1609.34:.1f} mi" if vis_m is not None else "N/A",
        "updateTime": local_time(cur["dt"], tz, "%a %-I:%M %p"),
        "cityForecast": forecast,
    }


def client_ip():
    # Behind a reverse proxy, the real client is the first X-Forwarded-For entry.
    # Only trust this header if your proxy sets it (otherwise use werkzeug's ProxyFix).
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() or request.remote_addr


# --------------------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get/conditions")
def get_conditions():
    q = request.args.get("q", "")
    try:
        if request.args.get("action") == "locate":
            name, lat, lon = geolocate(client_ip())
        else:
            name, lat, lon = geocode(q)
    except LookupError_ as e:
        return render_template("index.html", error=str(e), q=q), 404
    except requests.RequestException:
        return render_template("index.html", error="Weather service is unreachable. Try again shortly.", q=q), 502
    return redirect(url_for("conditions", lat=f"{lat:.4f}", lon=f"{lon:.4f}", name=name))


@app.route("/conditions")
def conditions():
    lat, lon = request.args.get("lat", type=float), request.args.get("lon", type=float)
    name = request.args.get("name", "")
    if lat is None or lon is None:
        if not USE_SAMPLE_DATA:
            return redirect(url_for("index"))
        lat, lon, name = 30.2672, -97.7431, "Austin, Texas, US"
    try:
        data = fetch_onecall(lat, lon)
    except requests.RequestException:
        return render_template("index.html", error="Weather service is unreachable. Try again shortly."), 502
    return render_template("conditions.html", **build_context(data, name or f"{lat:.2f}, {lon:.2f}"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
