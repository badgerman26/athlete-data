import requests
import os
import pandas as pd
from datetime import datetime

# --- CONFIG ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', API_KEY)

def final_attempt():
    print(f"Attempting to fetch activities for ID: {ATHLETE_ID}")
    
    # Intervals.icu requires the ID in the URL for the activities list
    # The endpoint is /athlete/{id}/activities-bulk or just /activities
    url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities"
    
    try:
        res = requests.get(url, auth=AUTH)
        
        if res.status_code == 200:
            activities = res.json()
            if not activities:
                return "SUCCESS: Connected, but the activity list is literally empty. Check your sync with Garmin/Strava."
            
            # Get the last ride
            latest = activities[-1]
            return f"MATCH! Found {len(activities)} activities. Latest: {latest.get('name')}"
            
        elif res.status_code == 405:
            return "ERROR 405: Still hitting the wrong door. Trying fallback..."
        else:
            return f"FAILED: Status {res.status_code}. Body: {res.text[:100]}"
            
    except Exception as e:
        return f"PYTHON ERROR: {str(e)}"

if __name__ == "__main__":
    result = final_attempt()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
