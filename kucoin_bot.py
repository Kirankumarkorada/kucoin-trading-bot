# 🚀 Render-Compatible KuCoin Bot
from flask import Flask
from threading import Thread
import ccxt
import time
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is running!", 200

def trading_bot():
    exchange = ccxt.kucoin({
        'apiKey': os.getenv('KUCOIN_API_KEY'),
        'secret': os.getenv('KUCOIN_SECRET'),
        'password': os.getenv('KUCOIN_PASSWORD'),
        'enableRateLimit': True
    })
    
    print("🤖 Bot started!")
    while True:
        try:
            ticker = exchange.fetch_ticker("SHIB/USDT")
            print(f"Price: {ticker['last']}")
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    Thread(target=trading_bot).start()
    app.run(host='0.0.0.0', port=10000)
