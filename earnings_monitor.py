import yfinance as yf 
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import time
import humanize
from dotenv import load_dotenv

# ================== CONFIG ==================

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
    "NVDA", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "AVGO", "TSM",
    "TSLA", "AMD", "MU", "INTC", "SPCX", "SNDK", "COIN", "DELL", "CRWV",
    "PYPL", "HOOD", "MSTR", "RBLX", "WDC", "PLTR", "ASML", "QCOM", "WMT", "BABA",
    # Add more if needed
}

DAYS_AHEAD = 10                    # Check today + next X days
CHECK_INTERVAL_SECONDS = None     # Set to 1800 for loop mode, or use cron
ALERTED_FILE = "alerted_earnings.json"
# ============================================


def send_telegram(message: str):

    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID is missing – cannot send Telegram message")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    # try:
    #     requests.post(url, json=payload, timeout=10)
    # except Exception as e:
    #     print(f"Telegram error: {e}")

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            print("✅ Telegram message sent successfully")
        else:
            print(f"❌ Telegram API error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


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
            ticker_data = ticker.get_info()
            if df is None or df.empty:
                continue

            # Filter for earnings in the next DAYS_AHEAD days
            start_date = today - timedelta(days=3)
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
                surprize = row.get("Surprise(%)")

                mcap = ticker_data.get("marketCap")
                trailPE = ticker_data.get("trailingPE")
                forwardPE = ticker_data.get("forwardPE")
                floatShares = ticker_data.get("floatShares")
                trailEPS = ticker_data.get("trailingEps")
                forwardEPS = ticker_data.get("forwardEps")
                shortRatio = ticker_data.get("shortRatio")
                cashflow = ticker_data.get("freeCashflow")


                est_str = f"${est_eps:.2f}" if pd.notna(est_eps) else "N/A"
                reported_str = f"${reported_eps:.2f}" if pd.notna(reported_eps) else "N/A (upcoming)"
                surprize_str = f"{surprize:.1f}%" if pd.notna(surprize) else "N/A"

                mcap_str = f"${humanize.intword(mcap)}" if pd.notna(mcap) else "N/A"
                trailPE_str = f"{trailPE:.2f}" if pd.notna(trailPE) else "N/A"
                forwardPE_str = f"{forwardPE:.2f}" if pd.notna(forwardPE) else "N/A"
                trailEPS_str = f"{trailEPS:.2f}" if pd.notna(trailEPS) else "N/A"
                forwardEPS_str = f"{forwardEPS:.2f}" if pd.notna(forwardEPS) else "N/A"
                shortRatio_str = f"{shortRatio:.2f}" if pd.notna(shortRatio) else "N/A"
                floatShares_str = f"{humanize.intword(floatShares)}" if pd.notna(floatShares) else "N/A"
                cashflow_str = f"${humanize.intword(cashflow)}" if pd.notna(cashflow) else "N/A"


                msg = (
                    f"🚨 <b>EARNINGS ALERT</b> — {symbol}\n\n"
                    f"<b>Date:</b> {date.date()}\n"
                    f"<b>Estimate EPS:</b> {est_str}\n"
                    f"<b>Reported EPS:</b> {reported_str}\n"
                    f"<b>Surprize:</b> {surprize_str}\n\n"

                    f"🚨 <b>FINANCIAL ALERT</b> — {symbol}\n\n"
                    f"<b>Market Cap:</b> {mcap_str}\n"
                    f"<b>Trailing PE:</b> {trailPE_str}\n"
                    f"<b>Forward PE:</b> {forwardPE_str}\n\n"
                    f"<b>Trailing EPS:</b> {trailEPS_str}\n"
                    f"<b>Forward EPS:</b> {forwardEPS_str}\n\n"
                    f"<b>Short Ratio:</b> {shortRatio_str}\n"
                    f"<b>Float Shares:</b> {floatShares_str}\n"
                    f"<b>Cashflow:</b> {cashflow_str}\n"
                    
                )

                # if pd.notna(row.get("Surprise(%)")):
                #     msg += f"<b>Surprise:</b> {row['Surprise(%)']:.1f}%\n"

                # msg += "\n<i>Data from Yahoo Finance (similar to TradingView)</i>"

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

    load_dotenv(override=True)
    global BOT_TOKEN, CHAT_ID
    # BOT_TOKEN = os.getenv("BOT_TOKEN")
    # CHAT_ID = os.getenv("CHAT_ID")

    BOT_TOKEN = os.getenv("secrets.BOT_TOKEN")
    CHAT_ID = os.getenv("secrets.CHAT_ID")

    print(f"BOT_TOKEN loaded: {bool(BOT_TOKEN)}")
    print(f"CHAT_ID loaded: {bool(CHAT_ID)}")

    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Secrets missing! Aborting.")
        exit(1)

    if CHECK_INTERVAL_SECONDS:
        while True:
            check_earnings()
            time.sleep(CHECK_INTERVAL_SECONDS)
    else:
        check_earnings()