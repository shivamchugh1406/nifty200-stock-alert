import requests
import pandas as pd
import json

# Step 1: Download the file
url = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
headers = {
    "User-Agent": "Mozilla/5.0"
}
response = requests.get(url, headers=headers)

# Step 2: Save it as CSV
with open("nifty_200.csv", "wb") as f:
    f.write(response.content)

# Step 3: Read CSV using pandas
df = pd.read_csv("nifty_200.csv")

# Step 4: Extract only the 'Symbol' column
symbols = df['Symbol'].dropna().tolist()  # Make sure there are no NaNs

# Step 5: Save symbols to a JSON file
with open("symbols.json", "w") as f:
    json.dump(symbols, f, indent=4)

print("✅ Done! symbols.json created with", len(symbols), "symbols.")