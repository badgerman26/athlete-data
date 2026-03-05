import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# Load credentials from GitHub Secrets
ATHLETE_ID = os.environ.get('ATHLETE_ID')
INTERVALS_KEY = os.environ.get('INTERVALS_KEY')

def fetch_intervals_data():
    # Fetch Wellness
    wellness_url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/wellness.csv"
    r_well = requests.get(wellness_url, auth=('API_KEY', INTERVALS_KEY))
    
    # Fetch Activities
    activities_url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities.csv"
    r_act = requests.get(activities_url, auth=('API_KEY', INTERVALS_KEY))
    
    if r_well.status_code == 200 and r_act.status_code == 200:
        # Save CSVs for history
        with open('wellness.csv', 'w') as f: f.write(r_well.text)
        with open('activities.csv', 'w') as f: f.write(r_act.text)
        
        # Create latest.json (Last 7 days of data)
        df_well = pd.read_csv('wellness.csv').tail(7)
        latest_data = df_well.to_dict(orient='records')
        
        with open('latest.json', 'w') as f:
            json.dump(latest_data, f, indent=4)
        print("Sync Complete: latest.json created.")
    else:
        print(f"Error: {r_well.status_code} / {r_act.status_code}")

if __name__ == "__main__":
    fetch_intervals_data()
