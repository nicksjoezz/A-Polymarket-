from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import time
import threading
import json
from engine import TradingEngine

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_123')
socketio = SocketIO(app, cors_allowed_origins="*")

STATE_FILE = 'bot_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Ensure it's not trading on start for safety
                state["is_trading"] = False
                return state
        except Exception as e:
            print(f"Error loading state: {e}")

    return {
        "is_trading": False,
        "metrics": {
            "total_trades": 0,
            "win_rate": 0,
            "total_profit": 0.0,
            "balance": 1000.0,
        },
        "total_scanned": 0,
        "scanned_markets": [],
        "open_positions": [],
        "resolved_positions": [],
        "news_events": [],
        "logs": ["Bot initialized..."],
        "dev_check_logs": [],
        "config": {
            "paper_mode": True,
            "trade_amount": 10.0,
            "min_edge": 0.20,
            "scan_interval": 1,
            "paper_balance": 1000.0,
            "max_trades": 10,
            "strategy": "Forecast Arbitrage"
        }
    }

def save_state():
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(bot_state, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

# Storage for bot state
bot_state = load_state()

engine = TradingEngine(bot_state, socketio, save_callback=save_state)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')
    if action == 'start':
        bot_state["is_trading"] = True
        bot_state["logs"].append("Trading started.")
        engine.start()
    elif action == 'stop':
        bot_state["is_trading"] = False
        bot_state["logs"].append("Trading stopped.")
        engine.stop()

    save_state()
    socketio.emit('bot_status', bot_state)
    return jsonify({"is_trading": bot_state["is_trading"]})

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    # Update config in bot_state
    for key in bot_state["config"]:
        if key in data:
            bot_state["config"][key] = data[key]

    bot_state["logs"].append("Configuration updated.")
    save_state()
    socketio.emit('bot_status', bot_state)
    return jsonify({"status": "success"})

@socketio.on('request_update')
def handle_request_update():
    emit('bot_status', bot_state)

def simulator_loop():
    while True:
        if bot_state["is_trading"]:
             # Periodically simulate market scan and positions for UI feedback
             time.sleep(15)
             engine.simulate_resolution()
        else:
             time.sleep(10)

if __name__ == '__main__':
    # Start simulator loop in a separate thread
    threading.Thread(target=simulator_loop, daemon=True).start()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
