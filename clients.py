import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
import os
import time
from dotenv import load_dotenv

load_dotenv()

GAMMA_API = "https://gamma-api.polymarket.com"

WEATHER_KEYWORDS = [
    "weather", "temperature", "hurricane", "tornado", "rainfall",
    "snowfall", "heatwave", "heat wave", "storm", "drought",
    "flood", "celsius", "fahrenheit", "el nino", "la nina",
    "wildfire", "cyclone", "typhoon", "blizzard", "monsoon",
    "wind speed", "precipitation", "solar storm",
    "daily high", "daily low",
]

WEATHER_TAG_LABELS = [
    "weather", "climate", "temperature", "hurricane",
    "tornado", "storm", "earthquake", "natural disaster",
    "daily temperature", "global temp", "flood", "wildfire",
    "hurricanes", "pandemics", "space",
]

class PolymarketClient:
    def __init__(self, private_key=None, paper_mode=True):
        self.paper_mode = paper_mode
        self.host = "https://clob.polymarket.com"
        self.key = private_key or os.getenv("PK")
        self.client = None
        if self.key and not self.paper_mode:
            self.client = ClobClient(self.host, key=self.key, chain_id=POLYGON)

    def get_weather_tags(self):
        try:
            resp = requests.get(f"{GAMMA_API}/tags", timeout=15)
            resp.raise_for_status()
            tags = resp.json()
            return [t for t in tags if any(kw in t.get("label", "").lower() for kw in WEATHER_TAG_LABELS)]
        except Exception:
            return []

    def get_events_by_tag(self, tag_id, limit=50):
        all_events = []
        offset = 0
        while True:
            try:
                resp = requests.get(f"{GAMMA_API}/events", params={
                    "tag_id": tag_id, "active": "true", "closed": "false",
                    "limit": limit, "offset": offset
                }, timeout=15)
                resp.raise_for_status()
                events = resp.json()
                if not events: break
                all_events.extend(events)
                offset += limit
                if len(events) < limit: break
                time.sleep(0.1)
            except Exception:
                break
        return all_events

    def search_weather_events(self, query="weather", limit=20):
        try:
            resp = requests.get(f"{GAMMA_API}/search", params={"q": query, "limit_per_type": limit}, timeout=15)
            resp.raise_for_status()
            results = resp.json()
            return results if isinstance(results, list) else results.get("events", [])
        except Exception:
            return []

    def get_weather_markets(self):
        """Combined discovery strategy for weather markets."""
        discovered = {} # dedupe by condition_id

        # Strategy 1: Tag-based
        tags = self.get_weather_tags()
        for tag in tags:
            events = self.get_events_by_tag(tag["id"])
            for event in events:
                for m in event.get("markets", []):
                    if m.get("conditionId") and m["conditionId"] not in discovered:
                        m["source"] = f"tag:{tag['label']}"
                        discovered[m["conditionId"]] = m

        # Strategy 2: Search
        for query in ["weather", "hurricane", "temperature"]:
            events = self.search_weather_events(query)
            for event in events:
                if isinstance(event, dict):
                    for m in event.get("markets", []):
                        if m.get("conditionId") and m["conditionId"] not in discovered:
                            m["source"] = f"search:{query}"
                            discovered[m["conditionId"]] = m

        # Strategy 3: Keyword scan (Last 2 pages for performance)
        try:
            for offset in [0, 50]:
                resp = requests.get(f"{GAMMA_API}/events", params={
                    "active": "true", "closed": "false", "limit": 50, "offset": offset, "order": "volume24hr", "ascending": "false"
                }, timeout=15)
                events = resp.json()
                for event in events:
                    combined = (event.get("title", "") + " " + event.get("description", "")).lower()
                    if any(kw in combined for kw in WEATHER_KEYWORDS):
                        for m in event.get("markets", []):
                            if m.get("conditionId") and m["conditionId"] not in discovered:
                                m["source"] = "keyword_scan"
                                discovered[m["conditionId"]] = m
        except Exception:
            pass

        return list(discovered.values())

    def get_orderbook(self, token_id):
        url = f"{self.host}/book?token_id={token_id}"
        response = requests.get(url)
        return response.json()

class WeatherClient:
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, lat, lon):
        params = {
            "latitude": lat, "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min", "timezone": "auto", "forecast_days": 1
        }
        try:
            response = requests.get(self.base_url, params=params)
            return response.json()
        except Exception:
            return None

class NewsClient:
    def get_weather_alerts(self):
        return [
            {"source": "USGS", "location": "Miami", "type": "Flood", "conf": 0.88, "desc": "Gauge above flood stage"},
            {"source": "NOAA", "location": "New York", "type": "Temperature", "conf": 0.95, "desc": "Record high forecast"}
        ]
