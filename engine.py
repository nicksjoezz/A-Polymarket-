import time
from datetime import datetime
import threading
from clients import PolymarketClient, WeatherClient
from strategies import StrategyEngine

class TradingEngine:
    def __init__(self, bot_state, socketio, save_callback=None):
        self.bot_state = bot_state
        self.socketio = socketio
        self.save_callback = save_callback
        self.pm_client = PolymarketClient(paper_mode=self.bot_state["config"]["paper_mode"])
        self.weather_client = WeatherClient()
        self.strategy_engine = StrategyEngine(self.bot_state["config"])
        self.is_running = False
        self.thread = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.bot_state["logs"].append("Trading engine started.")

    def stop(self):
        self.is_running = False
        self.bot_state["logs"].append("Trading engine stopping...")

    def run(self):
        while self.is_running:
            try:
                if self.bot_state["is_trading"]:
                    self.scan_and_trade()
                time.sleep(self.bot_state["config"]["scan_interval"] * 60)
            except Exception as e:
                self.bot_state["logs"].append(f"Error in engine: {str(e)}")
                time.sleep(60)

    def scan_and_trade(self):
        self.bot_state["logs"].append("Scanning markets...")
        markets_data = self.pm_client.get_markets()
        if not markets_data:
            return

        self.bot_state["total_scanned"] = len(markets_data)
        self.bot_state["scanned_markets"] = [
            {"id": m["id"], "question": m["question"], "volume": float(m.get("volume", 0)), "is_new": True}
            for m in markets_data
        ]
        self.socketio.emit('bot_status', self.bot_state)

        for market in markets_data:
            if not self.is_running or not self.bot_state["is_trading"]:
                break

            strategy_name = self.bot_state["config"]["strategy"]

            # Simple simulation of data fetching for strategy
            forecast = None
            if "Weather" in market.get("category", ""):
                 # In a real bot, we'd extract lat/lon from the market question
                 forecast = self.weather_client.get_forecast(40.7128, -74.0060) # New York

            signal = self.strategy_engine.get_signal(
                strategy_name,
                market,
                forecast=forecast,
                smart_wallets=self.bot_state.get("smart_wallets", {}),
                news_events=self.bot_state.get("news_events", [])
            )

            if signal:
                self.execute_trade(market, signal)

    def execute_trade(self, market, signal):
        # Check if already in position
        for p in self.bot_state["open_positions"]:
            if p["market_id"] == market["id"]:
                return

        amount = self.bot_state["config"]["trade_amount"]
        price = market.get("price", 0.5) # Simplified price fetching

        if self.bot_state["config"]["paper_mode"]:
            # Paper trading logic
            self.bot_state["metrics"]["balance"] -= amount
            position = {
                "market_id": market["id"],
                "question": market["question"],
                "side": signal["side"],
                "amount": amount,
                "price": price,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.bot_state["open_positions"].append(position)
            self.bot_state["metrics"]["total_trades"] += 1
            self.bot_state["logs"].append(f"Paper Trade: {signal['side']} on {market['question']} at ${price}")

            # Simulate dev check log
            dev_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market": market,
                "target_side": signal["side"],
                "analysis": f"Confidence: {signal['confidence']}, Edge: {signal['edge']}",
                "triggering_news": [],
                "vwap": price,
                "edge": signal["edge"]
            }
            self.bot_state["dev_check_logs"].append(dev_log)
            if self.save_callback:
                self.save_callback()
            self.socketio.emit('bot_status', self.bot_state)
        else:
            # Live trading logic would go here
            self.bot_state["logs"].append("Live trading is not fully implemented in this MVP.")

    def simulate_resolution(self):
        # Periodically resolve random open positions for simulation
        if self.bot_state["open_positions"]:
            pos = self.bot_state["open_positions"].pop(0)
            profit = pos["amount"] * 0.1 # Simulate 10% profit for the UI
            self.bot_state["metrics"]["balance"] += pos["amount"] + profit
            self.bot_state["metrics"]["total_profit"] += profit

            resolved = {
                "question": pos["question"],
                "side": pos["side"],
                "amount": pos["amount"],
                "profit": profit,
                "resolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.bot_state["resolved_positions"].append(resolved)
            self.bot_state["logs"].append(f"Position Resolved: {pos['question']} - Profit: ${profit:.2f}")
            if self.save_callback:
                self.save_callback()
            self.socketio.emit('bot_status', self.bot_state)
