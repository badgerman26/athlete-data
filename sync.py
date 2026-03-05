import requests
import os
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
# The documentation says username MUST be 'API_KEY'
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('API_KEY', KEY) 
ETAPE_DATE = datetime(2026, 7, 19)

def get_data():
    # Using '0' as the ID shortcut as per the docs you found
    url = "https://intervals.icu/api/v1/athlete/0/activities?limit=5"
    
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
        
        report = f"""
# COACH TONY: CONNECTION ESTABLISHED
**Last Session Found:** {name}
- **Distance:** {dist}km
- **Climbing:** {elev}m

**Tony's Verdict:** That 'API_KEY' username fix was the missing link. We are live.
"""
    else:
        report = f"# COACH TONY: STILL BLOCKED\nResponse: {data}"

    with open("latest_report.txt", "w") as f:
        f.write(report)
