import requests
import os
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
ID = os.environ.get('INTERVALS_ID')
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', KEY)
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # Looking back 10 days to ensure we never miss a ride
    start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    url = f"https://intervals.icu/api/v1/athlete/{ID}/activities?oldest={start}"
    
    try:
        r = requests.get(url, auth=AUTH)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

if __name__ == "__main__":
    activities = get_data()
    
    if activities and isinstance(activities, list):
        # Sort to find the latest session
        activities.sort(key=lambda x: x['start_date_local'], reverse=True)
        act = activities[0]
        
        # Metric Extraction
        name = act.get('name', 'Unknown Session')
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        elev = int(act.get('total_elevation_gain', 0))
        dist = round(act.get('distance', 0) / 1000, 1)
        type_ = act.get('type', 'Ride')
        
        report = f"""
# COACH TONY: RIDE DEBRIEF
**Last Session:** {name} ({type_})

## The Stats
- **Distance:** {dist}km
- **Climbing:** {elev}m ascent
- **Threshold Work (Z4):** {z4}m
- **Days to L'Etape:** {(ETAPE_DATE - datetime.now()).days}

**Tony's Verdict:** {"Solid vertical gain. Your legs will thank you in the Alps." if elev > 300 else "Good aerobic maintenance. Consistency is king."}
"""
    else:
        report = f"""
# COACH TONY: CONNECTION ERROR
The server responded but no data was parsed. 
Current ID: {ID}
Ensure your ID in GitHub Secrets is ONLY numbers (156193).
"""

    with open("latest_report.txt", "w") as f:
        f.write(report)
