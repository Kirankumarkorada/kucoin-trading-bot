# 🍪 SIMPLE KUCOIN BOT FOR $5 (UPDATED FOR RENDER)
from flask import Flask
from threading import Thread
import ccxt
import time
import os

# ===== FLASK SETUP (KEEPS BOT ONLINE) =====
app = Flask(__name__)

# Fix favicon error
@app.route('/favicon.ico')
def favicon():
    return "", 200

# Health check for UptimeRobot
@app.route('/')
def home():
    return "🤖 Bot is running!", 200

# ===== TRADING BOT LOGIC =====
def trading_bot():
    # KuCoin API setup
    exchange = ccxt.kucoin({
        'apiKey': os.getenv('KUCOIN_API_KEY'),
        'secret': os.getenv('KUCOIN_SECRET'),
        'password': os.getenv('KUCOIN_PASSWORD'),
        'enableRateLimit': True
    })
    
    print("🤖 Trading bot started!")
    while True:
        try:
            # Get SHIB price
            ticker = exchange.fetch_ticker("SHIB/USDT")
            price = ticker['last']
            print(f"SHIB Price: ${price:.8f}")
            
            # Your trading strategy here (example: buy dips)
            # (We'll add this later when you're ready)
            
            time.sleep(60)  # Check every 1 minute
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(30)

# ===== RUN BOTH SERVERS =====
if __name__ == "__main__":
    Thread(target=trading_bot).start()  # Start trading bot
    app.run(host='0.0.0.0', port=10000)  # Keep Render happy
