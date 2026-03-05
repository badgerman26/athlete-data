import requests
import pandas as pd
import os
from datetime import datetime, timedelta

# --- CONFIG ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
AUTH = ('athlete', API_KEY)
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # We ask for a massive range to ensure we catch today's ride
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        r = requests.get(f"{BASE_URL}/activities?oldest={start}&newest={end}", auth=AUTH)
        r.raise_for_status()
        activities = r.json()
        
        # Wellness call
        w = requests.get(f"{BASE_URL}/wellness?oldest={start}&newest={end}", auth=AUTH)
        wellness = w.json()
        
        return activities, wellness
    except Exception as e:
        print(f"Error: {e}")
        return [], []

if __name__ == "__main__":
    activities, wellness = get_data()
    
    if not activities:
        report = "# COACH TONY: ERROR\nNo activities found in the last 30 days. Check API permissions."
    else:
        # SORTING: Ensure we get the actual latest ride
        activities.sort(key=lambda x: x['start_date_local'], reverse=True)
        act = activities[0]
        
        # Data Extraction
        name = act.get('name', 'Unknown')
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        elev = int(act.get('total_elevation_gain', 0))
        hr = act.get('average_heartrate', 0)
        dist = round(act.get('distance', 0) / 1000, 1)

        report = f"""
# COACH TONY: RIDE DEBRIEF
**Session:** {name} | **Distance:** {dist}km
**Days to Etape:** {(ETAPE_DATE - datetime.now()).days}

- **Z4 Stimulus:** {z4}m
- **Hills:** {elev}m ascent
- **Avg HR:** {hr} bpm

**Tony's Verdict:** {"You're putting in the work. Solid session." if z4 > 10 or elev > 100 else "Recovery/Maintenance miles. Keep the engine turning."}
"""

    with open("latest_report.txt", "w") as f:
        f.write(report)
    
    if activities: pd.DataFrame(activities).to_csv("activities.csv", index=False)
    if wellness: pd.DataFrame(wellness).to_csv("wellness.csv", index=False)
