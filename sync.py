import requests
import os
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', API_KEY)

def final_push():
    # Looking back 7 days. Simplest possible request.
    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # We are using the "Bulk" endpoint which is often more permissive
    url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities?oldest={start}"
    
    try:
        res = requests.get(url, auth=AUTH)
        if res.status_code == 200:
            data = res.json()
            return f"VICTORY: Found {len(data)} activities."
        else:
            return f"STILL 403: Check if your ID ({ATHLETE_ID}) matches the Key owner."
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    report = final_push()
    with open("latest_report.txt", "w") as f:
        f.write(report)
