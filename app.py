from flask import Flask, render_template
import json
import os
from datetime import datetime

# Path to the data file where crossed stocks are stored
DATA_FILE = "crossed_stocks.json"

app = Flask(__name__)

def load_crossed_stocks_from_file():
    """
    Loads the list of crossed stocks (with details) from the JSON file.
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

@app.route("/")
def index():
    """
    Renders the main page, displaying stocks that have crossed their last month's high.
    """
    crossed_stocks_list = load_crossed_stocks_from_file()
    last_updated_time = "N/A"
    if os.path.exists(DATA_FILE):
        try:
            last_modified_timestamp = os.path.getmtime(DATA_FILE)
            last_updated_time = datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%d %H:%M:%S IST')
        except Exception as e:
            print(f"Could not get last modified time for {DATA_FILE}: {e}")

    # The 'stocks' variable passed to the template will now be a list of dictionaries
    return render_template("index.html", stocks=crossed_stocks_list, last_updated=last_updated_time)

if __name__ == "__main__":
    print("Starting Flask web server...")
    app.run(debug=True, host='0.0.0.0', port=5000)