import os
import time
import ccxt
import requests
import pandas as pd
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# KuCoin Credentials
api_key = os.getenv("KUCOIN_API_KEY")
api_secret = os.getenv("KUCOIN_SECRET")
api_passphrase = os.getenv("KUCOIN_PASSPHRASE")

# Telegram Bot
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Settings
symbols = ["BTC/USDT", "ETH/USDT"]
timeframe = "5m"
max_trade_amount = 4.5
take_profit = 1.02
trailing_stop_loss_pct = 0.98
cooldown_minutes = 30
min_usdt_balance = 4.0
trade_start_hour = 9
trade_end_hour = 21
daily_profit_target = 5.0
daily_drawdown_limit = -5.0

# Internal State File
state_file = "bot_state.json"
state = {
    "in_position": False,
    "last_entry_price": 0.0,
    "cooldown_until": None,
    "daily_profit": 0.0,
    "daily_drawdown": 0.0,
    "trailing_stop_price": 0.0,
    "active_symbol": None
}

exchange = ccxt.kucoin({
    'apiKey': api_key,
    'secret': api_secret,
    'password': api_passphrase,
    'enableRateLimit': True
})


def load_state():
    global state
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)


def save_state():
    with open(state_file, "w") as f:
        json.dump(state, f)


def send_telegram(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            data={"chat_id": telegram_chat_id, "text": message}
        )
    except Exception as e:
        print("Telegram Error:", e)


def fetch_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["ema"] = df["close"].ewm(span=20).mean()
    df["rsi"] = df["close"].rolling(window=14).apply(lambda x: (100 - (100 / (1 + ((x.diff().clip(lower=0).sum()) / abs(x.diff().clip(upper=0).sum()))))) if len(x.dropna()) == 14 else None)
    df["ema_short"] = df["close"].ewm(span=12).mean()
    df["ema_long"] = df["close"].ewm(span=26).mean()
    df["macd"] = df["ema_short"] - df["ema_long"]
    df["signal"] = df["macd"].ewm(span=9).mean()
    return df.dropna()


def should_buy(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    return latest["macd"] > latest["signal"] and prev["macd"] < prev["signal"] and latest["close"] > latest["ema"] and latest["rsi"] < 40


def get_usdt_balance():
    balance = exchange.fetch_balance()
    return balance['total']['USDT']


def place_buy(symbol):
    global state
    usdt = get_usdt_balance()
    if usdt < min_usdt_balance:
        send_telegram("⚠️ Not enough USDT to trade.")
        return
    price = exchange.fetch_ticker(symbol)['ask']
    amount = round(max_trade_amount / price, 6)
    exchange.create_market_buy_order(symbol, amount)
    state.update({
        "last_entry_price": price,
        "in_position": True,
        "trailing_stop_price": price * trailing_stop_loss_pct,
        "active_symbol": symbol
    })
    send_telegram(f"✅ Bought {amount} {symbol.split('/')[0]} at {price:.2f} USDT")
    save_state()


def place_sell(reason):
    global state
    symbol = state["active_symbol"]
    balance = exchange.fetch_balance()
    coin = symbol.split('/')[0]
    amount = balance['free'].get(coin, 0)
    if amount > 0:
        price = exchange.fetch_ticker(symbol)['bid']
        exchange.create_market_sell_order(symbol, amount)
        pl_pct = (price - state["last_entry_price"]) / state["last_entry_price"] * 100
        profit_usdt = (price - state["last_entry_price"]) * amount
        msg = f"❌ Sold {coin} at {price:.2f} USDT\nReason: {reason}\nP/L: {pl_pct:.2f}%"
        send_telegram(msg)
        state.update({
            "in_position": False,
            "daily_profit": state["daily_profit"] + profit_usdt,
            "daily_drawdown": state["daily_drawdown"] + profit_usdt,
            "trailing_stop_price": 0.0,
            "active_symbol": None
        })
        if "STOP" in reason:
            state["cooldown_until"] = time.time() + cooldown_minutes * 60
        save_state()


load_state()

while True:
    try:
        now = datetime.now()
        if now.hour < trade_start_hour or now.hour >= trade_end_hour:
            time.sleep(60)
            continue

        if state["cooldown_until"] and time.time() < state["cooldown_until"]:
            time.sleep(60)
            continue

        if state["daily_profit"] >= daily_profit_target or state["daily_drawdown"] <= daily_drawdown_limit:
            print("✅ Daily limit reached.")
            time.sleep(300)
            continue

        if not state["in_position"]:
            for symbol in symbols:
                df = fetch_data(symbol)
                if should_buy(df):
                    place_buy(symbol)
                    break
        else:
            symbol = state["active_symbol"]
            df = fetch_data(symbol)
            current_price = df.iloc[-1]["close"]

            # Update trailing stop
            if current_price > state["trailing_stop_price"] / trailing_stop_loss_pct:
                state["trailing_stop_price"] = current_price * trailing_stop_loss_pct
                save_state()

            if current_price >= state["last_entry_price"] * take_profit:
                place_sell("TAKE PROFIT")
            elif current_price <= state["trailing_stop_price"]:
                place_sell("TRAILING STOP")

        time.sleep(60)

    except Exception as e:
        send_telegram(f"⚠️ Bot Error:\n{e}")
        time.sleep(60)

