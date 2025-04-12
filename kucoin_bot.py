# 🚀 KuCoin $5 Trading Bot (Railway Version)
import ccxt
import time
import os
from datetime import datetime

# ===== CONFIG =====
SYMBOL = "SHIB/USDT"          # Best for small accounts
TRADE_AMOUNT = 1.5            # $1.50 per trade (meets KuCoin minimum)
TP_PERCENT = 2.0              # Take profit at 2%
SL_PERCENT = 1.0              # Stop loss at 1%
CHECK_INTERVAL = 60           # 1 minute checks (seconds)

# ===== KUCOIN SETUP =====
exchange = ccxt.kucoin({
    'apiKey': os.getenv('KUCOIN_API_KEY'),
    'secret': os.getenv('KUCOIN_SECRET'),
    'password': os.getenv('KUCOIN_PASSWORD'),
    'enableRateLimit': True
})

# ===== STATE =====
trade_state = {
    'in_position': False,
    'entry_price': 0,
    'position_size': 0,
    'total_pnl': 0.0
}

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def execute_order(side):
    global trade_state
    try:
        if side == 'buy':
            price = exchange.fetch_ticker(SYMBOL)['last']
            amount = TRADE_AMOUNT / price
            if amount * price < 1.0:  # KuCoin minimum check
                log("⚠️ Order too small - skipping")
                return False
                
            order = exchange.create_market_order(SYMBOL, 'buy', amount)
            trade_state.update({
                'in_position': True,
                'entry_price': order['price'],
                'position_size': order['amount']
            })
            log(f"✅ BUY {order['amount']:.0f} {SYMBOL.split('/')[0]} at ${order['price']:.8f}")
            return True
            
        elif side == 'sell':
            balance = exchange.fetch_balance()[SYMBOL.split('/')[0]]['free']
            order = exchange.create_market_order(SYMBOL, 'sell', balance)
            pnl = (order['price'] - trade_state['entry_price']) * trade_state['position_size']
            trade_state.update({
                'in_position': False,
                'total_pnl': trade_state['total_pnl'] + pnl
            })
            log(f"💰 SELL | PnL: ${pnl:.4f} | Total: ${trade_state['total_pnl']:.4f}")
            return True
            
    except Exception as e:
        log(f"❌ Order failed: {str(e)}")
        return False

def check_market():
    try:
        latest = exchange.fetch_ticker(SYMBOL)
        price = latest['last']
        
        if not trade_state['in_position']:
            # Buy if price drops 1% from last check
            if price <= latest['open'] * 0.99:
                execute_order('buy')
                
        elif trade_state['in_position']:
            current_pnl = ((price - trade_state['entry_price']) / trade_state['entry_price']) * 100
            if current_pnl >= TP_PERCENT or current_pnl <= -SL_PERCENT:
                execute_order('sell')
                
    except Exception as e:
        log(f"⚠️ Market check error: {str(e)}")

if __name__ == "__main__":
    log("🤖 Bot started - Waiting for opportunities...")
    while True:
        check_market()
        time.sleep(CHECK_INTERVAL)
