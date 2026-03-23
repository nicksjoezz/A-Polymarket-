import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
import os
from dotenv import load_dotenv

load_dotenv()

class PolymarketClient:
    def __init__(self, private_key=None, paper_mode=True):
        self.paper_mode = paper_mode
        self.host = "https://clob.polymarket.com"
        self.key = private_key or os.getenv("PK")
        self.client = None
        if self.key and not self.paper_mode:
            self.client = ClobClient(self.host, key=self.key, chain_id=POLYGON)
            # self.client.set_api_creds(...) # Need to set API credentials if using real trading

    def get_markets(self, next_cursor=""):
        url = f"https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
        if next_cursor:
            url += f"&next_cursor={next_cursor}"
        response = requests.get(url)
        return response.json()

    def get_market(self, condition_id):
        url = f"https://gamma-api.polymarket.com/markets/{condition_id}"
        response = requests.get(url)
        return response.json()

    def get_orderbook(self, token_id):
        url = f"{self.host}/book?token_id={token_id}"
        response = requests.get(url)
        return response.json()

    def get_price_history(self, token_id):
        # Placeholder for price history
        return []

class WeatherClient:
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, lat, lon):
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 1
        }
        response = requests.get(self.base_url, params=params)
        return response.json()

class NewsClient:
    def get_weather_alerts(self):
        # In a real bot, we'd poll api.weather.gov or USGS
        return [
            {"source": "USGS", "location": "Miami", "type": "Flood", "conf": 0.88, "desc": "Gauge above flood stage"},
            {"source": "NOAA", "location": "New York", "type": "Temperature", "conf": 0.95, "desc": "Record high forecast"}
        ]
