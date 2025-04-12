# 🚀 KuCoin $5 Bot - Optimized for Micro Accounts
import ccxt
import time
import pandas as pd
import os
from datetime import datetime

# === CONFIG (ADJUST THESE!) === ⚡️
SYMBOL = "DOGE/USDT"          # Only trade 1 coin
INITIAL_CAPITAL = 5.0          # Your $5
RISK_PER_TRADE = 0.10          # Risk $0.10 per trade (2%)
TP_PERCENT = 3.0               # 3% take profit 
SL_PERCENT = 1.5               # 1.5% stop loss
CHECK_INTERVAL = 300           # 5-min checks (avoid rate limits)

# === KuCoin Setup === ⚡️ Removed proxies
exchange = ccxt.kucoin({
    'apiKey': os.getenv('KUCOIN_API_KEY'),
    'secret': os.getenv('KUCOIN_SECRET'),
    'password': os.getenv('KUCOIN_PASSWORD'),
    'enableRateLimit': True
})

# === State ===
trade_state = {
    'in_position': False,
    'entry_price': 0,
    'position_size': 0,
    'pnl': 0.0
}

# === Telegram Alerts ===
def send_alert(msg):
    try:
        token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': msg})
    except:
        pass  # Fail silently if no internet

# === Get Indicators === ⚡️ Simplified strategy
def get_indicators():
    ohlcv = exchange.fetch_ohlcv(SYMBOL, '15m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # EMA Crossover
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    
    # RSI Filter
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.iloc[-1]  # Latest candle

# === Position Sizing === ⚡️ Fixed for $5 accounts
def calculate_size():
    balance = exchange.fetch_balance()['USDT']['free']
    risk_amount = min(RISK_PER_TRADE, balance * 0.02)  # Max 2% risk
    ticker = exchange.fetch_ticker(SYMBOL)
    size = risk_amount / (ticker['last'] * (SL_PERCENT/100))
    return round(size, 2)  # Round to 2 decimals

# === Trade Execution === ⚡️ Added fee checks
def execute_trade(side):
    global trade_state
    try:
        if side == 'buy':
            size = calculate_size()
            if size * exchange.fetch_ticker(SYMBOL)['last'] < 1.0:  # KuCoin minimum
                send_alert("⚠️ Order too small - add funds")
                return False
            
            order = exchange.create_market_order(SYMBOL, 'buy', size)
            trade_state.update({
                'in_position': True,
                'entry_price': order['price'],
                'position_size': order['amount']
            })
            send_alert(f"✅ BUY {SYMBOL} at {order['price']}")
            return True
            
        elif side == 'sell':
            order = exchange.create_market_order(SYMBOL, 'sell', trade_state['position_size'])
            pnl = (order['price'] - trade_state['entry_price']) * trade_state['position_size']
            trade_state.update({
                'in_position': False,
                'pnl': trade_state['pnl'] + pnl
            })
            send_alert(f"💰 SELL {SYMBOL} | PnL: ${pnl:.2f}")
            return True
            
    except Exception as e:
        send_alert(f"❌ Trade failed: {str(e)}")
        return False

# === Strategy Logic === ⚡️ Conservative entries
def check_strategy():
    latest = get_indicators()
    price = exchange.fetch_ticker(SYMBOL)['last']
    
    # Entry: EMA crossover + RSI not overbought
    if not trade_state['in_position']:
        if (latest['ema9'] > latest['ema21']) and (latest['rsi'] < 60):
            execute_trade('buy')
    
    # Exit: TP/SL or 24h timeout
    elif trade_state['in_position']:
        pnl_pct = ((price - trade_state['entry_price']) / trade_state['entry_price']) * 100
        if pnl_pct >= TP_PERCENT or pnl_pct <= -SL_PERCENT:
            execute_trade('sell')

# === Main Loop ===
def run():
    send_alert(f"🤖 Bot started with ${INITIAL_CAPITAL}")
    while True:
        try:
            check_strategy()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            send_alert(f"⚠️ Bot error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    run()
