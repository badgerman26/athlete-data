import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta

# Configuration
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = "API_KEY"
INTERVALS_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = (API_KEY, INTERVALS_KEY)
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"

def fetch_data():
    # Fetch Wellness
    pd.read_csv(f"{BASE_URL}/wellness.csv", storage_options={'Authorization': f'Basic {requests.auth._basic_auth_str(API_KEY, INTERVALS_KEY)}'}).to_csv('wellness.csv', index=False)
    # Fetch Activities
    pd.read_csv(f"{BASE_URL}/activities.csv", storage_options={'Authorization': f'Basic {requests.auth._basic_auth_str(API_KEY, INTERVALS_KEY)}'}).to_csv('activities.csv', index=False)
    # Fetch Events
    r = requests.get(f"{BASE_URL}/events", auth=AUTH)
    with open('events.json', 'w') as f:
        json.dump(r.json(), f)

def post_ride_audit():
    df = pd.read_csv('activities.csv')
    df['start_date_local'] = pd.to_datetime(df['start_date_local'])
    today = datetime.now().date()
    
    # Filter for today's ride
    todays_ride = df[df['start_date_local'].dt.date == today]
    
    if not todays_ride.empty:
        ride = todays_ride.iloc[0]
        # Calculate Efficiency Factor (EF)
        ef = round(ride['icu_weighted_avg_watts'] / ride['average_heartrate'], 2) if ride['average_heartrate'] > 0 else 0
        # Calculate Decoupling (Standard Intervals.icu field)
        drift = ride.get('pwr_hr_ergi', "N/A")
        
        summary = {
            "name": ride['name'],
            "watts": ride['icu_weighted_avg_watts'],
            "hr": ride['average_heartrate'],
            "ef": ef,
            "drift": drift,
            "tsb_next": ride['icu_training_load'] # Simplified for now
        }
        with open('latest_audit.json', 'w') as f:
            json.dump(summary, f)
        print("Audit Complete: New ride detected.")

if __name__ == "__main__":
    fetch_data()
    post_ride_audit()
