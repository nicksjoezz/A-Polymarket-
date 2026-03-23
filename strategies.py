import random
from datetime import datetime
import re

class Strategy:
    def __init__(self, name, config):
        self.name = name
        self.config = config

    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        raise NotImplementedError

class ForecastArbitrage(Strategy):
    """
    Strategy 1: Forecast Arbitrage
    Compare official weather forecast probability for a temperature bucket against Polymarket's price.
    When gap exceeds 15–20 percentage points, trade the underpriced side.
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        if not forecast or 'daily' not in forecast:
            return None

        # Extract temp range from market question (e.g., "43-45°F" or "above 50°F")
        question = market['question'].lower()
        forecast_temp = forecast['daily']['temperature_2m_max'][0]
        current_price = market.get('price', 0.5)

        # Basic range extraction
        match = re.search(r'(\d+)\s*-\s*(\d+)', question)
        if match:
            low, high = int(match.group(1)), int(match.group(2))
            if low <= forecast_temp <= high:
                # If forecast is in range, but price is low (< 0.30 as per research example)
                if current_price < 0.30:
                    return {"side": "YES", "confidence": 0.95, "edge": 0.70 - current_price}
            else:
                # If forecast is outside range, but price is high
                if current_price > 0.70:
                    return {"side": "NO", "confidence": 0.95, "edge": current_price - 0.30}

        return None

class TemperatureLaddering(Strategy):
    """
    Strategy 2: Temperature Laddering
    When a weather model shows high confidence that temperature falls within a 4–6 degree band,
    simultaneously buy YES on all buckets within that band.
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        if not forecast or 'daily' not in forecast:
            return None

        # Logic: If we see multiple buckets in the forecast band, we 'ladder' them
        # In a real bot, this would coordinate across multiple markets in a group
        # Here we'll simulate the 'buy' signal for a single bucket if it's in the band
        forecast_temp = forecast['daily']['temperature_2m_max'][0]
        question = market['question'].lower()

        # 4-6 degree band around the forecast
        band_low = forecast_temp - 2.5
        band_high = forecast_temp + 2.5

        match = re.search(r'(\d+)\s*-\s*(\d+)', question)
        if match:
            m_low, m_high = int(match.group(1)), int(match.group(2))
            # If market bucket overlaps with our 5-degree high-confidence band
            if m_low >= band_low and m_high <= band_high:
                 price = market.get('price', 0.1)
                 if price < 0.25: # "Total cost must be less than $1.00 * confidence"
                     return {"side": "YES", "confidence": 0.85, "edge": 0.40}

        return None

class NOBiasExploitation(Strategy):
    """
    Section 2.1: The NO Bias
    Retail traders disproportionately buy YES. YES overpricing at $0.20–$0.50 is the biggest NO edge.
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        yes_price = market.get('price', 0.5)
        # Biggest historical edge zone for NO buyers is between $0.20 and $0.50
        if 0.20 <= yes_price <= 0.50:
            return {"side": "NO", "confidence": 0.85, "edge": 0.30}
        elif 0.50 < yes_price <= 0.80:
            return {"side": "NO", "confidence": 0.70, "edge": 0.15}
        return None

class DisasterEarlyWarning(Strategy):
    """
    Strategy 3: Disaster & Flood Early Warning
    Exploit lag between official data (USGS, NHC, GloFAS) and Polymarket.
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        if not news_events:
            return None

        question = market['question'].lower()
        for event in news_events:
            # Match news location/type to market question
            if event['location'].lower() in question or event['type'].lower() in question:
                if event['conf'] > 0.75: # "High conviction trade"
                    price = market.get('price', 0.5)
                    if price < 0.40: # "But Polymarket still pricing below 40%"
                        return {"side": "YES", "confidence": 0.90, "edge": 0.50}
        return None

class BlackSwanBets(Strategy):
    """
    Strategy 4: Black Swan Tail Bets
    Target systematic underpricing of extreme events (priced at $0.02–$0.08).
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        price = market.get('price', 0.5)
        # Research: buy at $0.02–$0.08 per share when models show tail probability
        if 0.01 <= price <= 0.08:
            # Simplification: if it's a tail event market, we take a small bet
            if "extreme" in market['question'].lower() or "record" in market['question'].lower():
                return {"side": "YES", "confidence": 0.60, "edge": 0.80}
        return None

class SmartMoneyTracker(Strategy):
    """
    Section 8: Smart-Money Trader Tracking Edge
    Follow skilled traders when they converge on the same side.
    """
    def analyze_market(self, market, forecast=None, smart_wallets=None, news_events=None):
        if not smart_wallets:
            return None

        market_id = market['id']
        # If we have multiple high-skill traders moving on this market
        if market_id in smart_wallets:
             flow = smart_wallets[market_id]
             if flow.get('convergence_score', 0) > 0.7:
                 return {"side": flow['direction'], "confidence": 0.90, "edge": 0.30}
        return None

class StrategyEngine:
    def __init__(self, config):
        self.strategies = {
            "Forecast Arbitrage": ForecastArbitrage("Forecast Arbitrage", config),
            "Temperature Laddering": TemperatureLaddering("Temperature Laddering", config),
            "Disaster Early Warning": DisasterEarlyWarning("Disaster Early Warning", config),
            "Black Swan Bets": BlackSwanBets("Black Swan Bets", config),
            "NO Bias": NOBiasExploitation("NO Bias", config),
            "Smart-Money Tracker": SmartMoneyTracker("Smart-Money Tracker", config)
        }

    def get_signal(self, strategy_name, market, **kwargs):
        strategy = self.strategies.get(strategy_name)
        if strategy:
            return strategy.analyze_market(market, **kwargs)
        return None
