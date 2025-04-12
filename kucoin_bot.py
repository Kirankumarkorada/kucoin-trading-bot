# 🚀 KUCOIN SUPER BOT (v5.0) - Advanced but Safe for $5
from flask import Flask
from threading import Thread
import ccxt
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime

app = Flask(__name__)

# ===== CONFIG =====
RISK_PER_TRADE = 0.5  # 0.5% of balance per trade ($0.025)
MIN_TRADE_USDT = 1.0  # KuCoin minimum
SCAN_INTERVAL = 300   # 5 mins (avoid rate limits)

# ===== STRATEGY PARAMS =====
STRATEGIES = {
    'scalp': {
        'coins': ['SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT'],  # Low-cap volatile coins
        'timeframe': '1m',
        'rsi_buy': (25, 40),
        'take_profit': 0.8,  # 0.8%
        'stop_loss': 0.5     # 0.5%
    },
    'swing': {
        'coins': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],  # Higher market cap
        'timeframe': '15m',
        'ema_fast': 9,
        'ema_slow': 21,
        'take_profit': 2.5,  # 2.5%
        'stop_loss': 1.5      # 1.5%
    }
}

# ===== INIT EXCHANGE =====
exchange = ccxt.kucoin({
    'apiKey': os.getenv('KUCOIN_API_KEY'),
    'secret': os.getenv('KUCOIN_SECRET'),
    'password': os.getenv('KUCOIN_PASSWORD'),
    'enableRateLimit': True
})

# ===== UTILITIES =====
def get_indicators(df, strategy):
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain/loss))
    
    # EMAs
    if strategy == 'swing':
        df['ema_fast'] = df['close'].ewm(span=STRATEGIES[strategy]['ema_fast']).mean()
        df['ema_slow'] = df['close'].ewm(span=STRATEGIES[strategy]['ema_slow']).mean()
    
    return df.iloc[-1]  # Return latest candle

def calculate_position_size(balance, price):
    risk_amount = balance * (RISK_PER_TRADE / 100)
    amount = risk_amount / price
    return amount if amount * price >= MIN_TRADE_USDT else 0

# ===== TRADING ENGINE =====
def trading_bot():
    print("🔥 SUPER BOT ACTIVATED - Scanning for opportunities")
    
    while True:
        try:
            balance = exchange.fetch_balance()['USDT']['free']
            if balance < MIN_TRADE_USDT:
                print(f"⚠️ Low balance: ${balance:.2f} - Waiting...")
                time.sleep(SCAN_INTERVAL)
                continue
                
            for strategy, params in STRATEGIES.items():
                for symbol in params['coins']:
                    try:
                        # Get OHLCV data
                        ohlcv = exchange.fetch_ohlcv(symbol, params['timeframe'], limit=100)
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        
                        # Calculate indicators
                        latest = get_indicators(df, strategy)
                        
                        # Strategy Logic
                        if strategy == 'scalp':
                            if latest['rsi'] < params['rsi_buy'][1] and latest['rsi'] > params['rsi_buy'][0]:
                                price = exchange.fetch_ticker(symbol)['last']
                                amount = calculate_position_size(balance, price)
                                if amount > 0:
                                    print(f"🎯 SCALP BUY {symbol} at ${price:.8f}")
                                    exchange.create_market_order(symbol, 'buy', amount)
                                    # Place OCO order
                                    exchange.create_order(symbol, 'limit', 'sell', amount, price * (1 + params['take_profit']/100), {
                                        'stopPrice': price * (1 - params['stop_loss']/100),
                                        'type': 'stopLimit'
                                    })
                                    
                        elif strategy == 'swing':
                            if latest['ema_fast'] > latest['ema_slow'] and latest['ema_fast'] > latest['close'] * 0.99:
                                price = exchange.fetch_ticker(symbol)['last']
                                amount = calculate_position_size(balance, price)
                                if amount > 0:
                                    print(f"📈 SWING BUY {symbol} at ${price:.8f}")
                                    exchange.create_market_order(symbol, 'buy', amount)
                                    # Place OCO order
                                    exchange.create_order(symbol, 'limit', 'sell', amount, price * (1 + params['take_profit']/100), {
                                        'stopPrice': price * (1 - params['stop_loss']/100),
                                        'type': 'stopLimit'
                                    })
                                    
                    except Exception as e:
                        print(f"⚠️ {symbol} error: {str(e)}")
                        time.sleep(10)
            
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            print(f"🚨 CRITICAL ERROR: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    Thread(target=trading_bot).start()
    app.run(host='0.0.0.0', port=10000)
