# wx-everywhere
## Inspiration
We are a team of Meteorology majors with a strong background in Python, so building something in our main language that could also benefit an underserved group of people felt right!
## What it does
- User inputs their location in one of a few formats ("City" [not accurate], "City, ST" [USA], "City, ST, Country", "City, Country", or in ICAO/IATA airport codes
- Server uses local datasets and remote API to determine a lat/lon for a specified location
- Server reaches out to OpenWeatherMap and retrieves current conditions, alerts, and forecast data for the specified location
- Server then serves this as rendered HTML to the client via Flask
## How we built it
We decided to build with Flask because it's essentially a python-native web development platform. For our frontend, we used Bootstrap 5. We decided to go with OpenWeatherMap because of their worldwide API.
## Challenges we ran into
- API Limits: We ended up surpassing the daily free limit of 1,000 requests in testing, so we did have to purchase a subscription to the OneCall API. For every additional request over 1,000, it costs $0.0015, so this was not a big deal.
- HTML compatibility: Some older clients were not able to render Bootstrap 5 (One client is an iPhone 4 running iOS 7.1.2, and Bootstrap requires at least iOS 10), so we had to build in some simpler, HTML native pages for older clients.
## Accomplishments that we're proud of
WeatherEverywhere loads on average X-Y times *faster* than the USA's weather.gov, a service provided by the National Weather Service & the Department of Commerce.
## What we learned
Building something like this is simple, so long as you don't try to fill it with features that bog down your bandwith.
## What's next for WeatherEverywhere
We would like to continue working on this project, and perhaps look in to adding some simple data visualizations for the hourly forecast and other variables.
