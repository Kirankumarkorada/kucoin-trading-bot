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

# === Proxy Support (Updated Germany Proxy) ===
proxies = {
    "http": "http://116.203.151.31:8080",
    "https": "http://116.203.151.31:8080"
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
    'proxies': proxies  # <--- Apply proxies to KuCoin client
})

state = {
    symbol: {
        'in_position': False,
        'entry_price': 0,
        'profit_total': 0.0,
        'daily_pnl': 0.0
    } for symbol in symbols
}

# [Functions remain unchanged from your provided version]
# All 'requests.get' and 'requests.post' already use 'proxies=proxies'

# === End of Bot ===

if __name__ == "__main__":
    run_bot()

