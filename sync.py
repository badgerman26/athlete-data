import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta

# Configuration from GitHub Secrets
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = "API_KEY"
INTERVALS_KEY = os.environ.get('INTERVALS_API_KEY')

# Authentication Header
AUTH = (API_KEY, INTERVALS_KEY)
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"

def fetch_wellness():
    print("Fetching Wellness Data...")
    url = f"{BASE_URL}/wellness.csv"
    r = requests.get(url, auth=AUTH)
    if r.status_code == 200:
        with open('wellness.csv', 'wb') as f:
            f.write(r.content)
    else:
        print(f"Wellness Error: {r.status_code}")

def fetch_activities():
    print("Fetching Activities...")
    url = f"{BASE_URL}/activities.csv"
    r = requests.get(url, auth=AUTH)
    if r.status_code == 200:
        with open('activities.csv', 'wb') as f:
            f.write(r.content)
    else:
        print(f"Activities Error: {r.status_code}")

def fetch_events():
    print("Fetching Calendar Events (Planned & A-Events)...")
    start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
    url = f"{BASE_URL}/events?oldest={start}&newest={end}"
    r = requests.get(url, auth=AUTH)
    if r.status_code == 200:
        # Save as JSON to preserve structured workout details
        with open('events.json', 'w') as f:
            json.dump(r.json(), f)
    else:
        print(f"Events Error: {r.status_code}")

def upload_planned_workout():
    # Looks for a file created by Gemini to push back to Intervals
    if os.path.exists('planned_workout.json'):
        print("Found a new planned workout. Uploading...")
        with open('planned_workout.json', 'r') as f:
            payload = json.load(f)
        url = f"{BASE_URL}/events"
        r = requests.post(url, auth=AUTH, json=payload)
        if r.status_code == 200:
            print("Successfully pushed to Intervals.icu.")
            os.remove('planned_workout.json')
        else:
            print(f"Upload failed: {r.status_code} - {r.text}")

if __name__ == "__main__":
    fetch_wellness()
    fetch_activities()
    fetch_events()
    upload_planned_workout()
