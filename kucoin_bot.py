# 🚀 KuCoin Multi-Coin Smart Scalping Bot (Low Budget Optimized with Proxy Support)

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

# === Proxy Support ===
kucoin_proxy = {
    "http": "http://116.203.151.31:8080",
    "https": "http://116.203.151.31:8080"
}

news_proxy = {
    "http": "http://51.158.68.133:8811",
    "https": "http://51.158.68.133:8811"
}

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
    'proxies': kucoin_proxy  # <--- KuCoin uses Germany proxy
})

state = {
    symbol: {
        'in_position': False,
        'entry_price': 0,
        'profit_total': 0.0,
        'daily_pnl': 0.0
    } for symbol in symbols
}

# ✅ Updated request-based proxy functions

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        requests.post(url, data={'chat_id': telegram_chat_id, 'text': msg}, proxies=news_proxy)
    except Exception as e:
        print(f"[Telegram Error] {e}")

def news_filter():
    try:
        url = "https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news"
        res = requests.get(url, proxies=news_proxy)
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

# === End of Bot ===

if __name__ == "__main__":
    run_bot()
