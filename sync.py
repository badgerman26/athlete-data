import requests
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
AUTH = ('athlete', API_KEY)
ETAPE_DATE = datetime(2026, 7, 19)

# ROBBIE'S REAL BASELINES
HRV_MIN, RHR_MAX = 25, 56

def get_data():
    try:
        r_act = requests.get(f"{BASE_URL}/activities", auth=AUTH)
        r_act.raise_for_status()
        oldest = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        r_well = requests.get(f"{BASE_URL}/wellness?oldest={oldest}", auth=AUTH)
        r_well.raise_for_status()
        return r_act.json(), r_well.json()
    except Exception as e:
        print(f"API Error: {e}")
        return [], []

def generate_morning_report(wellness):
    if not wellness: return "No wellness data found."
    latest = wellness[-1]
    rmssd = latest.get('hrv', 'N/A')
    # Use .get() with multiple possible names for SDNN
    sdnn = latest.get('hrv_sdnn') or latest.get('sdnn', 'N/A')
    rhr = latest.get('restingHR', 'N/A')
    sleep = round(latest.get('sleepSecs', 0) / 3600, 1)
    
    status = "GO"
    if isinstance(rhr, (int, float)) and rhr > RHR_MAX: status = "CAUTION"
    if isinstance(rmssd, (int, float)) and rmssd < HRV_MIN: status = "CAUTION"
    
    days_to_etape = (ETAPE_DATE - datetime.now()).days

    return f"""
# COACH TONY: MORNING READINESS
**Status: {status}** | **Days to L'Etape: {days_to_etape}**

## Autonomic Audit
- **rMSSD (Recovery):** {rmssd} ms
- **SDNN (Total Stress):** {sdnn} ms
- **Sleeping HR:** {rhr} bpm
- **Sleep:** {sleep}h

**Tony's Strategy:** {"System is primed. Stay on plan." if status == "GO" else "Metrics are flagging. Zone 2 only."}
"""

def generate_post_activity_report(activities):
    if not activities: return "No activity data found."
    act = activities[-1]
    name = act.get('name', 'Unknown')
    type = act.get('type', 'Other')
    days_to_etape = (ETAPE_DATE - datetime.now()).days

    if type in ['Ride', 'VirtualRide']:
        z4 = round(act.get('time_in_z4', 0) / 60, 1)
        z5 = round(act.get('time_in_z5', 0) / 60, 1)
        elev = act.get('total_elevation_gain', 0)
        hr = act.get('average_heartrate', 'N/A')
        
        return f"""
# COACH TONY: RIDE DEBRIEF
**Session:** {name} | **Days to Etape: {days_to_etape}**

## Performance Audit
- **Z4/Z5 Quality:** {z4 + z5}m
- **Hills:** {elev}m ascent
- **Avg HR:** {hr} bpm

**Tony's Verdict:** {"Good durability." if z4 > 15 else "Focus on time-in-zone."}
"""
    else:
        return f" # COACH TONY: {type.upper()} REPORT\nActivity: {name}\nNote: Good consistent movement."

if __name__ == "__main__":
    activities, wellness = get_data()
    now = datetime.now()
    
    # Logic to decide which report to write to file
    if now.hour == 8:
        report = generate_morning_report(wellness)
    else:
        report = generate_post_activity_report(activities)

    with open("latest_report.txt", "w") as f:
        f.write(report)
    
    # Push data to repo
    if activities: pd.DataFrame(activities).to_csv("activities.csv", index=False)
    if wellness: pd.DataFrame(wellness).to_csv("wellness.csv", index=False)
