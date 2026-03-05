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
        # AGGRESSIVE FETCH: Grab the last 10 activities regardless of date
        r_act = requests.get(f"{BASE_URL}/activities?limit=10", auth=AUTH)
        r_act.raise_for_status()
        
        # Grab the last 14 wellness entries
        r_well = requests.get(f"{BASE_URL}/wellness?limit=14", auth=AUTH)
        r_well.raise_for_status()
        
        return r_act.json(), r_well.json()
    except Exception as e:
        print(f"Sync Error: {e}")
        return [], []

def generate_morning_report(wellness):
    if not wellness: return "Coach Tony: Waiting for wellness sync..."
    latest = wellness[-1]
    rmssd = latest.get('hrv', 0)
    sdnn = latest.get('hrv_sdnn') or latest.get('sdnn', 0)
    rhr = latest.get('restingHR', 0)
    status = "GO" if (rmssd >= HRV_MIN and rhr <= RHR_MAX) else "CAUTION"
    
    return f"""
# COACH TONY: MORNING READINESS
**Status: {status}** | Days to L'Etape: {(ETAPE_DATE - datetime.now()).days}

- **rMSSD:** {rmssd} ms | **SDNN:** {sdnn} ms
- **Resting HR:** {rhr} bpm
**Tony's Strategy:** {"System stable. Fuel for the build." if status == "GO" else "Stress is high. Cap power at Z2."}
"""

def generate_post_activity_report(activities):
    if not activities: return "Coach Tony: No activities found in Intervals.icu history."
    
    # Sort by start_date_local to ensure we have the absolute latest
    df_temp = pd.DataFrame(activities)
    df_temp['start_date_local'] = pd.to_datetime(df_temp['start_date_local'])
    act = df_temp.sort_values('start_date_local').iloc[-1].to_dict()
    
    z4 = round(act.get('time_in_z4', 0) / 60, 1)
    hr = act.get('average_heartrate', 0)
    elev = act.get('total_elevation_gain', 0)
    dist = round(act.get('distance', 0) / 1000, 1)
    
    return f"""
# COACH TONY: ACTIVITY DEBRIEF
**Session:** {act.get('name')} | **Distance:** {dist}km

- **Intensity (Z4):** {z4}m
- **Climbing:** {int(elev)}m ascent
- **Avg HR:** {hr} bpm
**Tony's Verdict:** {"Solid climbing work for the Ridgeway." if elev > 150 else "Good aerobic maintenance miles."}
"""

if __name__ == "__main__":
    activities, wellness = get_data()
    now = datetime.now()
    
    # Decide which report to generate
    if now.hour == 8:
        report = generate_morning_report(wellness)
    else:
        # This will now pull the absolute latest activity from your last 10
        report = generate_post_activity_report(activities)

    with open("latest_report.txt", "w") as f:
        f.write(report)
    
    # Save files to repo
    if activities: pd.DataFrame(activities).to_csv("activities.csv", index=False)
    if wellness: pd.DataFrame(wellness).to_csv("wellness.csv", index=False)
