import os
import requests
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
import time
import pandas as pd
import ta

# Load API keys
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret, testnet=True)

# Telegram Bot Details
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trading config
symbol = "BTCUSDT"
quantity = 0.001  # Small for testnet

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def get_klines(symbol, interval='1m', limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines)
    df = df.iloc[:, 0:6]
    df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
    df['close'] = df['close'].astype(float)
    return df

def strategy_rsi(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    if df['rsi'].iloc[-1] < 30:
        return 'BUY'
    elif df['rsi'].iloc[-1] > 70:
        return 'SELL'
    else:
        return 'HOLD'

def place_order(order_type):
    try:
        if order_type == 'BUY':
            order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
        elif order_type == 'SELL':
            order = client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
        return order
    except Exception as e:
        send_telegram_alert(f"Order Error: {str(e)}")
        return None

# Main bot loop
def run_bot():
    last_signal = ''
    while True:
        df = get_klines(symbol)
        signal = strategy_rsi(df)
        if signal != last_signal and signal != 'HOLD':
            order = place_order(signal)
            if order:
                send_telegram_alert(f"New Signal: {signal}\nOrder Executed.")
                last_signal = signal
        else:
            print(f"No action - {signal}")
        time.sleep(60)

if __name__ == "__main__":
    send_telegram_alert("🚀 Bot Started...")
    run_bot()

