import os
import time
import ccxt
import requests
import pandas as pd
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

# Bot Settings
symbol = "BTC/USDT"
timeframe = "5m"
max_trade_amount = 4.5  # USDT (keep some for fees)
take_profit = 1.02      # 2% TP
stop_loss = 0.98        # 2% SL
cooldown_minutes = 30   # after SL, rest
min_usdt_balance = 4.0

# Internal State
in_position = False
last_entry_price = 0
cooldown_until = None

# Initialize Exchange
exchange = ccxt.kucoin({
    'apiKey': api_key,
    'secret': api_secret,
    'password': api_passphrase,
    'enableRateLimit': True
})


# 💬 Telegram Notify
def send_telegram(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            data={"chat_id": telegram_chat_id, "text": message}
        )
    except Exception as e:
        print("Telegram Error:", e)


# 📊 Get Latest OHLCV Data
def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["rsi"] = df["close"].rolling(window=14).apply(lambda x: (100 - (100 / (1 + ((x.diff().clip(lower=0).sum()) / abs(x.diff().clip(upper=0).sum()))))) if len(x.dropna()) == 14 else None)
    df["ema"] = df["close"].ewm(span=20).mean()
    return df.dropna()


# 📈 Entry Conditions
def should_buy(df):
    latest = df.iloc[-1]
    if latest["close"] > latest["ema"] and latest["rsi"] < 35:
        return True
    return False


# 💰 Get Balance
def get_usdt_balance():
    balance = exchange.fetch_balance()
    return balance['total']['USDT']


# 🚀 Buy Order
def place_buy():
    global in_position, last_entry_price
    usdt = get_usdt_balance()
    if usdt < min_usdt_balance:
        send_telegram("⚠️ Not enough USDT to trade.")
        return
    price = exchange.fetch_ticker(symbol)['ask']
    amount = round(max_trade_amount / price, 6)
    order = exchange.create_market_buy_order(symbol, amount)
    last_entry_price = price
    in_position = True
    send_telegram(f"✅ Bought {amount} {symbol.split('/')[0]} at {price:.2f} USDT")
    return order


# 📤 Sell Order
def place_sell(reason):
    global in_position, cooldown_until
    balance = exchange.fetch_balance()
    coin = symbol.split('/')[0]
    amount = balance['free'].get(coin, 0)
    if amount > 0:
        price = exchange.fetch_ticker(symbol)['bid']
        order = exchange.create_market_sell_order(symbol, amount)
        profit_loss = (price - last_entry_price) / last_entry_price * 100
        msg = f"❌ Sold {coin} at {price:.2f} USDT\nReason: {reason}\nP/L: {profit_loss:.2f}%"
        send_telegram(msg)
        in_position = False
        if "STOP" in reason:
            cooldown_until = time.time() + (cooldown_minutes * 60)
        return order
    return None


# 📦 Daily Log
def log_trade(msg):
    with open("trade_log.csv", "a") as f:
        f.write(f"{datetime.now()},{msg}\n")


# 🔁 Main Loop
while True:
    try:
        if cooldown_until and time.time() < cooldown_until:
            print("🕑 Cooldown active...")
            time.sleep(60)
            continue

        df = fetch_data()

        if not in_position and should_buy(df):
            order = place_buy()
            log_trade(f"BUY,{last_entry_price}")
        elif in_position:
            current_price = df.iloc[-1]["close"]
            if current_price >= last_entry_price * take_profit:
                place_sell("TAKE PROFIT")
                log_trade(f"SELL-TP,{current_price}")
            elif current_price <= last_entry_price * stop_loss:
                place_sell("STOP LOSS")
                log_trade(f"SELL-SL,{current_price}")

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        send_telegram(f"⚠️ Bot Error:\n{e}")
        time.sleep(60)
