import time
from datetime import datetime, timedelta
from nsetools import Nse
import yfinance as yf
import json
import os
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import pandas as pd
import io

# --- Configuration ---
with open('recipients_email.txt', 'r') as f:
    email = [line.strip() for line in f]
RECIPIENT_EMAILS = email# Add more recipients as needed
SENDER_EMAIL = "sachdevavaibhav24@gmail.com"
with open('password.txt', 'r') as file:
    app_password = file.readline()
SENDER_PASSWORD = app_password # Get this from your Google Account's App Passwords

DATA_FILE = "crossed_stocks.json" # File to store crossed stock names

# Initialize NSETools
nse = Nse()

def get_nifty200_symbols():
    """
    Fetches the list of Nifty 200 stock symbols.
    Using a hardcoded list for demonstration.
    """
    print("Fetching Nifty 200 symbols...")
    nifty_200_symbols = [
        'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY', 'HINDUNILVR',
        'ITC', 'LT', 'SBIN', 'BHARTIARTL', 'BAJFINANCE', 'ASIANPAINT',
        'MARUTI', 'KOTAKBANK', 'AXISBANK', 'TITAN', 'ULTRACEMCO', 'SUNPHARMA',
        'NESTLEIND', 'ONGC', 'NTPC', 'POWERGRID', 'INDUSINDBK', 'TECHM',
        'WIPRO', 'ADANIENT', 'ADANIPORTS', 'JSWSTEEL', 'GRASIM', 'DIVISLAB'
        # Add more Nifty 200 stocks here or integrate a dynamic fetch
    ]
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    csv_file = io.StringIO(response.text)
    df = pd.read_csv(csv_file)
    # Convert to list of dicts (records) and save as JSON
    data = df.to_dict(orient="records")
    nifty_200_symbols = [i['Symbol'] for i in data]
    print(nifty_200_symbols)
    return nifty_200_symbols


def get_last_month_high(symbol):
    """
    Fetches the highest price for the given stock from the previous month.
    """
    today = datetime.now()
    first_day_current_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    start_date = first_day_previous_month.strftime('%Y-%m-%d')
    end_date = last_day_previous_month.strftime('%Y-%m-%d')

    try:
        data = yf.download(symbol + ".NS", start=start_date, end=end_date, progress=False, auto_adjust=True)
        if not data.empty:
            max_high = data['High'].max()
            if isinstance(max_high, (float, int)):
                return max_high
            elif hasattr(max_high, 'item'):
                return max_high.item()
            else:
                return float(max_high)
        return None
    except Exception as e:
        print(f"Error fetching historical data for {symbol} ({start_date} to {end_date}): {e}")
        return None

def get_live_price(symbol):
    """
    Fetches the current live price for the given stock.
    Tries nsetools first, then falls back to yfinance.
    """
    price = None
    try:
        quote = nse.get_quote(symbol)
        if quote and 'lastPrice' in quote and quote['lastPrice'] is not None:
            price = quote['lastPrice']
    except Exception as e:
        pass # print(f"nsetools error for {symbol}: {e}. Trying yfinance.")

    if price is None:
        try:
            ticker = yf.Ticker(symbol + ".NS")
            live_data = ticker.info
            if 'currentPrice' in live_data and live_data['currentPrice'] is not None:
                price = live_data['currentPrice']
            elif 'regularMarketPrice' in live_data and live_data['regularMarketPrice'] is not None:
                price = live_data['regularMarketPrice']
        except Exception as e:
            pass # print(f"yfinance error for {symbol}: {e}")

    if price is not None:
        if isinstance(price, (float, int)):
            return price
        elif hasattr(price, 'item'):
            return price.item()
        else:
            try:
                return float(price)
            except ValueError:
                print(f"Could not convert live price for {symbol} to float: {price}")
                return None
    return None

def send_notification_email(stock_name, live_price, last_month_high, recipients):
    """
    Sends an email notification.
    """
    subject = f"Stock Alert: {stock_name} Crossed Last Month High!"
    body = (
        f"Dear User,\n\n"
        f"This is an automated alert from your Stock Monitor application.\n\n"
        f"The stock **{stock_name}** has just crossed its last month's high.\n"
        f"  - Live Price: ₹{live_price:,.2f}\n"
        f"  - Last Month's High: ₹{last_month_high:,.2f}\n\n"
        f"Please check your trading platform for more details.\n\n"
        f"Regards,\n"
        f"Your Stock Monitor"
    )

    msg = MIMEText(body, 'plain', 'utf-8')
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"Email sent for {stock_name}")
    except Exception as e:
        print(f"Error sending email for {stock_name}: {e}")

def update_crossed_stocks_file(crossed_stocks_list):
    """
    Saves the list of crossed stocks (with details) to a JSON file.
    """
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(crossed_stocks_list, f, indent=4)
        print(f"Successfully wrote {len(crossed_stocks_list)} stocks to {os.path.abspath(DATA_FILE)}")
    except Exception as e:
        print(f"ERROR: Error writing to {DATA_FILE}: {e}")

def load_crossed_stocks_file():
    """
    Loads the list of crossed stocks (with details) from a JSON file.
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure loaded data is a list of dictionaries with expected keys
                if isinstance(data, list) and all(isinstance(item, dict) and 'symbol' in item and 'live_price' in item and 'last_month_high' in item for item in data):
                    return data
                else:
                    print(f"Warning: {DATA_FILE} content format mismatch. Returning empty list.")
                    return []
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {DATA_FILE}: {e}. Returning empty list.")
            return []
        except Exception as e:
            print(f"Error reading from {DATA_FILE}: {e}. Returning empty list.")
            return []
    return []

# --- Main Monitoring Logic ---

def monitor_stocks(nifty200_symbols):
    """
    The main function that monitors stocks, checks conditions, and triggers alerts.
    """
    print(f"Monitoring stocks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load previously crossed stocks from the file
    # Convert to a dictionary for faster lookups by symbol
    # This dictionary will also be used to build the new list for saving
    # It stores the symbol and a boolean indicating if an email was sent for it in this run
    previously_crossed_from_file = {
        item['symbol']: True for item in load_crossed_stocks_file()
    }
    print("previously_crossed_from_file =", previously_crossed_from_file)
    # This list will hold the stocks that are currently above their high
    # and will be saved to the JSON file.
    current_crossed_stocks_for_json = []

    

    for symbol in nifty200_symbols:
        live_price = get_live_price(symbol)
        last_month_high = get_last_month_high(symbol)

        if live_price is not None and last_month_high is not None:
            print(f"  {symbol}: Live Price = {live_price:.2f}, Last Month High = {last_month_high:.2f}")

            if live_price > last_month_high:
                # Add to the list that will be saved to the JSON
                current_crossed_stocks_for_json.append({
                    'symbol': symbol,
                    'live_price': round(live_price, 2),
                    'last_month_high': round(last_month_high, 2)
                })

                # Check if this stock was *not* previously recorded as crossed in the JSON file
                if symbol not in previously_crossed_from_file:
                    print(f"ALERT: {symbol} (Live: {live_price:.2f}) newly crossed last month high ({last_month_high:.2f})!")
                    send_notification_email(symbol, live_price, last_month_high, RECIPIENT_EMAILS)
                    # Mark as "sent" for this session to prevent immediate re-send
                    # (though the JSON will also prevent it in subsequent runs)
                    previously_crossed_from_file[symbol] = True # Mark as now recorded
                else:
                    print(f"  {symbol} is still above last month high. Not re-sending email.")
            else:
                # If a stock was previously in the JSON file but is now below its high,
                # it will automatically be excluded from current_crossed_stocks_for_json
                # and thus removed from the JSON on the next write.
                if symbol in previously_crossed_from_file:
                    print(f"  {symbol} has fallen below its last month high. Will be removed from display & future alerts.")


        else:
            print(f"  Could not get complete data for {symbol}. Skipping.")

    # Update the JSON file with the current list of stocks that are above their high
    update_crossed_stocks_file(current_crossed_stocks_for_json)
    print(f"Monitoring cycle finished. Stocks currently above high: {len(current_crossed_stocks_for_json)}")


# --- Scheduler Setup ---
nifty200_symbols = get_nifty200_symbols()
scheduler = BackgroundScheduler()
scheduler.add_job(monitor_stocks, 'interval', minutes=30, id='stock_monitor_job', args=[nifty200_symbols])

if __name__ == "__main__":
    print(f"Running from directory: {os.getcwd()}")
    print(f"Data file will be: {os.path.abspath(DATA_FILE)}")

    # Initial run before starting the scheduler
    monitor_stocks(nifty200_symbols) # Perform one check immediately on startup
    scheduler.start()

    try:
        # Keep the main thread alive for the scheduler to run in the background
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler shut down.")