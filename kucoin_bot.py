# 🚀 KUCOIN ULTRA BOT (v6.0) - All-In-One Solution
from flask import Flask
from threading import Thread
import ccxt
import pandas as pd
import numpy as np
import time
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ===== CONFIG ===== (EDIT THESE!)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')       # From @BotFather
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')   # Your chat ID
RISK_PER_TRADE = 1.0                               # 1% of balance
MIN_TRADE_USDT = 1.0                              # KuCoin minimum
ARBITRAGE_THRESHOLD = 0.5                         # 0.5% price difference

# ===== STRATEGY CONFIG =====
STRATEGIES = {
    'scalp': {
        'coins': ['SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT'],
        'timeframe': '1m',
        'rsi_buy': (28, 35),
        'take_profit': 0.9,
        'stop_loss': 0.6,
        'max_trades': 2
    },
    'swing': {
        'coins': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        'timeframe': '15m',
        'ema_fast': 9,
        'ema_slow': 21,
        'take_profit': 3.0,
        'stop_loss': 1.8,
        'max_trades': 1
    },
    'arbitrage': {
        'pairs': [('BTC/USDT', 'BTC/USDC'), ('ETH/USDT', 'ETH/USDC')],
        'threshold': ARBITRAGE_THRESHOLD
    }
}

# ===== INITIALIZE =====
exchange = ccxt.kucoin({
    'apiKey': os.getenv('KUCOIN_API_KEY'),
    'secret': os.getenv('KUCOIN_SECRET'),
    'password': os.getenv('KUCOIN_PASSWORD'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',
        'adjustForTimeDifference': True
    }
})

# ===== TELEGRAM ALERTS =====
def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

# ===== HYPEROPTIMIZED ENGINE =====
class TurboTradingEngine:
    def __init__(self):
        self.active_trades = {}
        self.last_arb_scan = 0
    
    def get_indicators(self, df, strategy):
        # Ultra-fast RSI
        close = df['close'].values
        deltas = np.diff(close)
        seed = deltas[:14]
        up = seed[seed >= 0].sum()/14
        down = -seed[seed < 0].sum()/14
        rs = up/down
        rsi = np.zeros_like(close)
        rsi[:14] = 100. - (100./(1.+rs))
        
        for i in range(14, len(close)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
                
            up = (up*13 + upval)/14
            down = (down*13 + downval)/14
            rs = up/down
            rsi[i] = 100. - (100./(1.+rs))
            
        df['rsi'] = rsi
        
        # Vectorized EMAs
        if strategy == 'swing':
            df['ema_fast'] = df['close'].ewm(
                span=STRATEGIES[strategy]['ema_fast'], 
                adjust=False
            ).mean()
            df['ema_slow'] = df['close'].ewm(
                span=STRATEGIES[strategy]['ema_slow'], 
                adjust=False
            ).mean()
        
        return df.iloc[-1]

    def check_arbitrage(self):
        if time.time() - self.last_arb_scan < 300:  # 5 min cooldown
            return
            
        self.last_arb_scan = time.time()
        for pair1, pair2 in STRATEGIES['arbitrage']['pairs']:
            try:
                ticker1 = exchange.fetch_ticker(pair1)
                ticker2 = exchange.fetch_ticker(pair2)
                spread = abs(ticker1['last'] - ticker2['last'])/ticker1['last']*100
                
                if spread > STRATEGIES['arbitrage']['threshold']:
                    message = (f"🚨 ARBITRAGE ALERT 🚨\n"
                              f"{pair1}: ${ticker1['last']:.8f}\n"
                              f"{pair2}: ${ticker2['last']:.8f}\n"
                              f"Spread: {spread:.2f}%")
                    send_alert(message)
                    
            except Exception as e:
                print(f"Arbitrage scan error: {e}")

    def execute_trade(self, symbol, strategy):
        try:
            balance = exchange.fetch_balance()['USDT']['free']
            if balance < MIN_TRADE_USDT:
                return False
                
            ohlcv = exchange.fetch_ohlcv(
                symbol, 
                STRATEGIES[strategy]['timeframe'], 
                limit=100
            )
            df = pd.DataFrame(ohlcv, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
            
            latest = self.get_indicators(df, strategy)
            price = exchange.fetch_ticker(symbol)['last']
            amount = (balance * (RISK_PER_TRADE/100)) / price
            
            if amount * price < MIN_TRADE_USDT:
                return False
                
            # Scalp Strategy
            if strategy == 'scalp':
                if (latest['rsi'] < STRATEGIES[strategy]['rsi_buy'][1] and 
                    latest['rsi'] > STRATEGIES[strategy]['rsi_buy'][0]):
                    
                    order = exchange.create_market_order(symbol, 'buy', amount)
                    send_alert(
                        f"⚡️ SCALP ENTRY ⚡️\n"
                        f"Coin: {symbol}\n"
                        f"Price: ${order['price']:.8f}\n"
                        f"Amount: {amount:.0f}\n"
                        f"TP: {STRATEGIES[strategy]['take_profit']}%\n"
                        f"SL: {STRATEGIES[strategy]['stop_loss']}%"
                    )
                    
                    # OCO Order
                    exchange.create_order(
                        symbol,
                        'limit',
                        'sell',
                        amount,
                        price * (1 + STRATEGIES[strategy]['take_profit']/100),
                        {
                            'stopPrice': price * (1 - STRATEGIES[strategy]['stop_loss']/100),
                            'type': 'stopLimit'
                        }
                    )
                    return True
            
            # Swing Strategy
            elif strategy == 'swing':
                if (latest['ema_fast'] > latest['ema_slow'] and 
                    latest['close'] > latest['ema_slow']):
                    
                    order = exchange.create_market_order(symbol, 'buy', amount)
                    send_alert(
                        f"📈 SWING ENTRY 📈\n"
                        f"Coin: {symbol}\n"
                        f"Price: ${order['price']:.8f}\n"
                        f"Amount: {amount:.0f}\n"
                        f"TP: {STRATEGIES[strategy]['take_profit']}%\n"
                        f"SL: {STRATEGIES[strategy]['stop_loss']}%"
                    )
                    
                    # OCO Order
                    exchange.create_order(
                        symbol,
                        'limit',
                        'sell',
                        amount,
                        price * (1 + STRATEGIES[strategy]['take_profit']/100),
                        {
                            'stopPrice': price * (1 - STRATEGIES[strategy]['stop_loss']/100),
                            'type': 'stopLimit'
                        }
                    )
                    return True
                    
        except Exception as e:
            send_alert(f"❌ TRADE FAILED: {str(e)}")
            print(f"Trade error: {e}")
            return False

# ===== MAIN BOT =====
engine = TurboTradingEngine()

def trading_bot():
    send_alert("🤖 ULTRA BOT ACTIVATED - Monitoring Markets")
    print("⚡ Turbo Engine Started ⚡")
    
    while True:
        try:
            # Check arbitrage opportunities
            engine.check_arbitrage()
            
            # Execute strategies
            for strategy in ['scalp', 'swing']:
                for symbol in STRATEGIES[strategy]['coins']:
                    if engine.execute_trade(symbol, strategy):
                        time.sleep(10)  # Rate limit
                        
            time.sleep(10)  # Main loop delay
            
        except Exception as e:
            send_alert(f"🚨 CRITICAL ERROR: {str(e)}")
            print(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    Thread(target=trading_bot).start()
    app.run(host='0.0.0.0', port=10000)
