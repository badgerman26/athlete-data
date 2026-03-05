import requests
import os
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', API_KEY)
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # We provide 'oldest' to satisfy the 422 error requirement
    # Looking back 30 days to ensure we catch your recent ride
    oldest_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities?oldest={oldest_date}"
    
    try:
        res = requests.get(url, auth=AUTH)
        if res.status_code == 200:
            return res.json()
        else:
            return f"FAILED: Status {res.status_code}. Body: {res.text[:100]}"
    except Exception as e:
        return f"PYTHON ERROR: {str(e)}"

if __name__ == "__main__":
    activities = get_data()
    
    if isinstance(activities, list) and len(activities) > 0:
        # Success! Sort to get the absolute latest
        activities.sort(key=lambda x: x['start_date_local'], reverse=True)
        act = activities[0]
        
        name = act.get('name', 'Unknown')
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        elev = int(act.get('total_elevation_gain', 0))
        dist = round(act.get('distance', 0) / 1000, 1)

        report = f"""
# COACH TONY: DATA REACHED
**Success! Found {len(activities)} recent activities.**

**Latest Session:** {name}
- **Distance:** {dist}km
- **Climbing:** {elev}m
- **Z4 Stimulus:** {z4}m

**Tony's Verdict:** Connection is established. Ready for final Coach Tony logic.
"""
    else:
        report = f"COACH TONY: Still trying to break through. {activities}"

    with open("latest_report.txt", "w") as f:
        f.write(report)
