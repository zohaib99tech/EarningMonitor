import yfinance as yf 
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import time

# ================== CONFIG ==================
BOT_TOKEN = "8269432210:AAGga3ElOcWdNuXY8etV8EPPoOqpTd7PIxk"      # ← Replace with your Telegram bot token
CHAT_ID = "7016991413"          # ← Replace with your chat ID

# Your tech watchlist (S&P 500 IT + Nasdaq 100 tech companies)
# WATCHLIST = {
#     "NVDA", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "AVGO",
#     "TSLA", "AMD", "MU", "INTC", "ORCL", "CSCO", "AMAT", "LRCX", "KLAC",
#     "PANW", "CRWD", "SNPS", "CDNS", "ADBE", "ACN", "ANET", "ADSK", "FTNT",
#     "DDOG", "PLTR", "NOW", "CRM", "WDAY", "INTU", "TXN", "ADI", "QCOM",
#     "MRVL", "MPWR", "ON", "TER", "ARM", "ASML", "SHOP", "APP", "SNOW",
#     "MDB", "NET", "ZS", "OKTA", "S", "CRWV", "RKLB", "DELL", "HPQ", "IBM",
#     "CTSH", "AKAM", "FFIV", "FICO", "PTC", "VRSN", "KEYS", "TDY", "ZBRA",
#     # Add more if needed
# }

WATCHLIST = {
    "NVDA", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "AVGO",
    "TSLA", "AMD", "MU", "INTC", "SPCX", "ZBRA",
    # Add more if needed
}

DAYS_AHEAD = 2                    # Check today + next X days
CHECK_INTERVAL_SECONDS = None     # Set to 1800 for loop mode, or use cron
ALERTED_FILE = "alerted_earnings.json"
# ============================================


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def load_alerted():
    if os.path.exists(ALERTED_FILE):
        with open(ALERTED_FILE, "r") as f:
            return json.load(f)
    return {}


def save_alerted(data):
    with open(ALERTED_FILE, "w") as f:
        json.dump(data, f)


def check_earnings():
    today = datetime.now().date()
    alerted = load_alerted()
    today_str = today.isoformat()

    if today_str not in alerted:
        alerted[today_str] = set()

    print(f"Checking earnings for {len(WATCHLIST)} tickers...")

    for symbol in sorted(WATCHLIST):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.get_earnings_dates(limit=8)  # Get recent + upcoming

            if df is None or df.empty:
                continue

            # Filter for earnings in the next DAYS_AHEAD days
            start_date = today
            end_date = today + timedelta(days=DAYS_AHEAD)

            mask = (df.index.date >= start_date) & (df.index.date <= end_date)
            upcoming = df[mask]

            if upcoming.empty:
                continue

            for date, row in upcoming.iterrows():
                key = f"{symbol}_{date.date()}"
                if key in alerted[today_str]:
                    continue

                est_eps = row.get("EPS Estimate")
                reported_eps = row.get("Reported EPS")

                est_str = f"${est_eps:.2f}" if pd.notna(est_eps) else "N/A"
                reported_str = f"${reported_eps:.2f}" if pd.notna(reported_eps) else "N/A (upcoming)"

                msg = (
                    f"🚨 <b>EARNINGS ALERT</b> — {symbol}\n\n"
                    f"<b>Date:</b> {date.date()}\n"
                    f"<b>Estimate EPS:</b> {est_str}\n"
                    f"<b>Previous/Reported EPS:</b> {reported_str}\n"
                )

                if pd.notna(row.get("Surprise(%)")):
                    msg += f"<b>Surprise:</b> {row['Surprise(%)']:.1f}%\n"

                msg += "\n<i>Data from Yahoo Finance (similar to TradingView)</i>"

                send_telegram(msg)
                print(f"✅ Alert sent for {symbol} on {date.date()}")
                # alerted[today_str].add(key)

        except Exception as e:
            print(f"Error with {symbol}: {e}")
            continue

    # save_alerted(alerted)
    print("Check complete.\n")


if __name__ == "__main__":
    print("=== Earnings Monitor Started (yfinance) ===")
    print(f"Monitoring {len(WATCHLIST)} tech companies")

    if CHECK_INTERVAL_SECONDS:
        while True:
            check_earnings()
            time.sleep(CHECK_INTERVAL_SECONDS)
    else:
        check_earnings()