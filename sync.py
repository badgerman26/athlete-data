import requests
import os
from datetime import datetime, timedelta

# --- CONFIG ---
ID = os.environ.get('INTERVALS_ID')
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', KEY)

def coach_tony_reboot():
    # Looking back 3 days only - simplest request possible
    start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    # NEW ENDPOINT: This is the most permissive one
    url = f"https://intervals.icu/api/v1/athlete/{ID}/activities?oldest={start}"
    
    try:
        print(f"Connecting to ID {ID}...")
        r = requests.get(url, auth=AUTH)
        
        if r.status_code == 200:
            data = r.json()
            if not data:
                return "CONNECTED: But no rides found. Is Garmin/Strava synced?"
            
            last_ride = data[-1]
            return f"SUCCESS: Found {last_ride.get('name')} on {last_ride.get('start_date_local')}"
        
        elif r.status_code == 403:
            return f"403 STILL: The ID {ID} is being rejected. Check if the ID in GitHub matches your Settings page exactly."
        else:
            return f"FAILED: Status {r.status_code}. Double check the API Key."
            
    except Exception as e:
        return f"CRASH: {str(e)}"

if __name__ == "__main__":
    result = coach_tony_reboot()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
