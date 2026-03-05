import requests
import os
import pandas as pd
from datetime import datetime

# --- CONFIG ---
ID = os.environ.get('INTERVALS_ID')
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', KEY)
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # We remove 'oldest' and use 'limit' to avoid timezone/date issues
    url = f"https://intervals.icu/api/v1/athlete/{ID}/activities?limit=10"
    
    try:
        r = requests.get(url, auth=AUTH)
        print(f"Server Status: {r.status_code}") # This helps us debug in the logs
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    activities = get_data()
    
    # Check if we got a valid list with at least one item
    if isinstance(activities, list) and len(activities) > 0:
        # Ensure we are looking at the most recent one
        activities.sort(key=lambda x: x['start_date_local'], reverse=True)
        act = activities[0]
        
        name = act.get('name', 'Unknown Session')
        # Time is in seconds, converting to minutes
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        elev = int(act.get('total_elevation_gain', 0))
        dist = round(act.get('distance', 0) / 1000, 1)
        type_ = act.get('type', 'Session')
        
        report = f"""
# COACH TONY: DATA DETECTED
**Last Session:** {name} ({type_})

## Performance Metrics
- **Distance:** {dist}km
- **Climbing:** {elev}m ascent
- **Z4 (Threshold):** {z4}m
- **Days to L'Etape:** {(ETAPE_DATE - datetime.now()).days}

**Tony's Verdict:** Finally found it. {elev}m of climbing is exactly what we need for the Alps.
"""
    else:
        report = f"""
# COACH TONY: EMPTY DATA ERROR
The connection worked (Status 200), but your activity list is empty.
This means Intervals.icu doesn't see your ride yet. 
Check: Intervals.icu > Settings > API Access (Ensure 'View Activities' is allowed).
"""

    with open("latest_report.txt", "w") as f:
        f.write(report)
