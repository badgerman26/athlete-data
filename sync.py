import requests
import os
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('API_KEY', KEY) 
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # 'oldest' is required by the server (Error 422 fix)
    # We look back 14 days to be safe
    oldest_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    
    # Using the '0' shortcut which we now know works with your key
    url = f"https://intervals.icu/api/v1/athlete/0/activities?oldest={oldest_date}"
    
    try:
        r = requests.get(url, auth=AUTH)
        if r.status_code == 200:
            return r.json()
        else:
            return f"Error {r.status_code}: {r.text}"
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    data = get_data()
    
    if isinstance(data, list) and len(data) > 0:
        # Sort to get the latest ride
        data.sort(key=lambda x: x['start_date_local'], reverse=True)
        act = data[0]
        
        name = act.get('name', 'Unknown Session')
        dist = round(act.get('distance', 0) / 1000, 1)
        elev = int(act.get('total_elevation_gain', 0))
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        
        report = f"""
# COACH TONY: CONNECTION SUCCESSFUL
**Last Session Found:** {name}

## The Stats
- **Distance:** {dist}km
- **Climbing:** {elev}m ascent
- **Z4 Stimulus:** {z4}m
- **Days to L'Etape:** {(ETAPE_DATE - datetime.now()).days}

**Tony's Verdict:** The gate is open. We've got your {dist}km session data. 
"""
    else:
        report = f"# COACH TONY: DATA ERROR\nResponse: {data}"

    with open("latest_report.txt", "w") as f:
        f.write(report)
