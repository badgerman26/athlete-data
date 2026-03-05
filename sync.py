import requests
import os

# --- CONFIG ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', API_KEY)

def debug_sync():
    # 1. Test the most basic 'Athlete' endpoint
    print(f"Testing connection for Athlete ID: {ATHLETE_ID}")
    res = requests.get(f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}", auth=AUTH)
    
    if res.status_code != 200:
        return f"CRITICAL ERROR: API returned status {res.status_code}. Your API Key or Athlete ID is wrong."

    # 2. Test the Activity endpoint with NO filters
    act_res = requests.get(f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities", auth=AUTH)
    activities = act_res.json()
    
    if not isinstance(activities, list):
        return f"ERROR: Expected a list of activities, but got: {type(activities)}"
    
    if len(activities) == 0:
        return "SUCCESSFUL CONNECTION, BUT ZERO ACTIVITIES. Check Intervals.icu -> Settings -> API Key Permissions (ensure 'View Activities' is checked)."

    # 3. If we actually find data, show me the most recent one
    latest = activities[-1]
    return f"DATA FOUND! Latest Activity: {latest.get('name')} on {latest.get('start_date_local')}. Total found: {len(activities)}"

if __name__ == "__main__":
    result = debug_sync()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
