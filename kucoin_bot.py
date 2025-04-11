# 🚀 KuCoin Multi-Coin Smart Scalping Bot (Low Budget Optimized)

import ccxt
import time
import pandas as pd
import requests
import os
from datetime import datetime
import openai

# === API Keys ===
kucoin_api_key = os.getenv('KUCOIN_API_KEY')
kucoin_secret = os.getenv('KUCOIN_SECRET')
kucoin_password = os.getenv('KUCOIN_PASSWORD')
telegram_token = os.getenv('TELEGRAM_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
openai.api_key = os.getenv('OPENAI_API_KEY')

# === Optimized Symbols for Low Budget ===
symbols = [
    'DOGE/USDT',
    'SHIB/USDT',
    'PEPE/USDT',
    'FLOKI/USDT'
]

min_usdt_trade_value = 1.5  # Keep trade minimum to avoid errors
investment_ratio = 0.5
scalp_tp_percent = 0.5
scalp_sl_percent = 0.3
news_keywords = ["crash", "exploit", "hacked", "SEC", "lawsuit"]

exchange = ccxt.kucoin({
    'apiKey': kucoin_api_key,
    'secret': kucoin_secret,
    'password': kucoin_password,
    'enableRateLimit': True,
})

state = {
    symbol: {
        'in_position': False,
        'entry_price': 0,
        'profit_total': 0.0,
        'daily_pnl': 0.0
    } for symbol in symbols
}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        requests.post(url, data={'chat_id': telegram_chat_id, 'text': msg})
    except Exception as e:
        print(f"[Telegram Error] {e}")

def log_trade(symbol, side, price, amount, pnl=0):
    with open("trade_log.csv", "a") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{now},{symbol},{side},{price},{amount},{pnl:.4f}\n")

def fetch_trade_amounts():
    try:
        balance = exchange.fetch_balance()['USDT']['free']
        budget = balance * investment_ratio / len(symbols)
        prices = {symbol: exchange.fetch_ticker(symbol)['last'] for symbol in symbols}

        trade_amounts = {}
        for symbol in symbols:
            price = prices[symbol]
            amount = budget / price
            value = amount * price
            trade_amounts[symbol] = round(amount, 2 if 'DOGE' in symbol or 'SHIB' in symbol or 'PEPE' in symbol or 'FLOKI' in symbol else 4) if value >= min_usdt_trade_value else 0.0
        return trade_amounts
    except Exception as e:
        send_telegram(f"❌ Trade amount fetch error: {e}")
        return {symbol: 0.0 for symbol in symbols}

def check_scalp_signal(df):
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    if df['rsi'].iloc[-1] < 30 and df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
        return 'buy'
    elif df['rsi'].iloc[-1] > 70 and df['ema9'].iloc[-1] < df['ema21'].iloc[-1]:
        return 'sell'
    return None

def ai_confidence_score(symbol, signal):
    if signal is None:
        return 0.0
    try:
        prompt = f"Analyze the symbol {symbol}. The bot detected a {signal.upper()} signal based on RSI + EMA strategy. Should we proceed with the trade? Give a confidence score from 0 to 1."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content
        score = float([s for s in text.split() if s.replace('.', '', 1).isdigit()][-1])
        return score if score > 0.65 else 0.0
    except Exception as e:
        print(f"[AI Score Error] {e}")
        return 0.0

def news_filter():
    try:
        url = "https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news"
        res = requests.get(url)
        articles = res.json().get('results', [])
        for article in articles:
            for word in news_keywords:
                if word in article['title'].lower():
                    send_telegram(f"🛑 News Risk Detected: {article['title']}")
                    return False
        return True
    except Exception as e:
        print(f"[News Error] {e}")
        return True

def get_ohlcv(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"[OHLCV Error] {symbol}: {e}")
        return None

def place_order(symbol, side, trade_amounts):
    s = state[symbol]
    amount = trade_amounts.get(symbol, 0.0)
    if amount == 0:
        send_telegram(f"⚠️ Skipping {symbol}: Trade too small")
        return
    try:
        order = exchange.create_market_order(symbol, side, amount)
        time.sleep(2)
        full = exchange.fetch_order(order['id'], symbol)
        price = full['average']

        if side == 'buy':
            s['entry_price'] = price
            s['in_position'] = True
        else:
            pnl = (price - s['entry_price']) * amount
            s['profit_total'] += pnl
            s['daily_pnl'] += pnl
            s['entry_price'] = 0
            s['in_position'] = False
            send_telegram(f"💰 {symbol} PnL: {pnl:.4f} USDT\n📊 Total: {s['profit_total']:.4f} USDT")
            log_trade(symbol, side, price, amount, pnl)

        msg = f"📅 {side.upper()} {symbol}\nAmount: {amount}\nPrice: {price}"
        send_telegram(msg)
        print(msg)
        log_trade(symbol, side, price, amount)
    except Exception as e:
        send_telegram(f"❌ Order Error {symbol}: {e}")
        print(f"[Order Error] {e}")

def send_daily_summary():
    summary = "📊 Daily Profit Summary:\n"
    total = 0.0
    for symbol in symbols:
        pnl = state[symbol]['daily_pnl']
        summary += f"{symbol}: {pnl:.4f} USDT\n"
        total += pnl
        state[symbol]['daily_pnl'] = 0
    summary += f"Total: {total:.4f} USDT"
    send_telegram(summary)

def run_bot():
    send_telegram("🤖 Bot Started with Smart Low-Budget Strategy")
    summary_timer = time.time()
    while True:
        if not news_filter():
            print("🛑 News risk detected. Pausing trades.")
            time.sleep(300)
            continue

        trade_amounts = fetch_trade_amounts()
        for symbol in symbols:
            df = get_ohlcv(symbol)
            if df is None:
                continue
            signal = check_scalp_signal(df)
            score = ai_confidence_score(symbol, signal)
            price = df['close'].iloc[-1]
            s = state[symbol]

            if score == 0.0:
                print(f"AI filtered out weak {signal} signal for {symbol}")
                continue

            if not s['in_position'] and signal == 'buy':
                place_order(symbol, 'buy', trade_amounts)
            elif s['in_position']:
                tp = s['entry_price'] * (1 + scalp_tp_percent / 100)
                sl = s['entry_price'] * (1 - scalp_sl_percent / 100)
                if price >= tp:
                    send_telegram(f"🌟 TP HIT {symbol} at {price:.6f}")
                    place_order(symbol, 'sell', trade_amounts)
                elif price <= sl:
                    send_telegram(f"🛑 SL HIT {symbol} at {price:.6f}")
                    place_order(symbol, 'sell', trade_amounts)

        if time.time() - summary_timer > 86400:
            send_daily_summary()
            summary_timer = time.time()

        time.sleep(30)

if __name__ == "__main__":
    run_bot()
