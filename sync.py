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

# ROBBIE'S REAL BASELINES (Hard-coded to prevent error)
HRV_MIN, RHR_MAX = 25, 56

def get_data():
    r_act = requests.get(f"{BASE_URL}/activities", auth=AUTH)
    oldest = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    r_well = requests.get(f"{BASE_URL}/wellness?oldest={oldest}", auth=AUTH)
    return r_act.json(), r_well.json()

def generate_morning_report(wellness):
    latest = wellness[-1]
    rmssd = latest.get('hrv', 0)
    sdnn = latest.get('hrv_sdnn', 0)
    rhr = latest.get('restingHR', 0)
    sleep = round(latest.get('sleepSecs', 0) / 3600, 1)
    deep_m = latest.get('deepSleepSecs', 0) // 60
    
    # ImReady4Training Logic
    status = "GO"
    if rhr > RHR_MAX or rmssd < HRV_MIN: status = "CAUTION"
    if rhr > 60 or rmssd < 20: status = "REST"
        
    days_to_etape = (ETAPE_DATE - datetime.now()).days

    return f"""
# COACH TONY: MORNING READINESS (ImReady4Training)
**Status: {status}** | **Days to L'Etape: {days_to_etape}**

## Autonomic Audit
- **rMSSD (Recovery):** {rmssd} ms (Baseline: 28-35)
- **SDNN (Total Stress):** {sdnn} ms
- **Sleeping HR:** {rhr} bpm (Baseline: 48-52)
- **Sleep:** {sleep}h (Deep: {deep_m}m)

**Tony's Strategy:** {"Nervous system is primed. Hit your power targets today." if status == "GO" else "Recovery is lagging. Stay in Zone 2 to protect the build."}
"""

def generate_post_activity_report(activities):
    act = activities[-1]
    name = act.get('name', 'Unknown')
    type = act.get('type', 'Other')
    days_to_etape = (ETAPE_DATE - datetime.now()).days

    if type in ['Ride', 'VirtualRide']:
        z4_mins = round(act.get('time_in_z4', 0) / 60, 1)
        z5_mins = round(act.get('time_in_z5', 0) / 60, 1)
        elev = act.get('total_elevation_gain', 0)
        cadence = act.get('average_cadence', 0)
        hr = act.get('average_heartrate', 0)
        np = act.get('icu_normalized_watts', 0)
        vi = round(np / act.get('icu_average_watts', 1), 2)
        
        # Tony's Specific Insights
        climb_note = "Great torque for L'Etape climbs." if cadence < 75 and z4_mins > 10 else "Good fluid cadence."
        env = "INDOOR (ERG Focus)" if type == 'VirtualRide' else "OUTDOOR (Terrain Audit)"

        return f"""
# COACH TONY: RIDE DEBRIEF
**Session:** {name} | **Mode:** {env} | **Days to Etape: {days_to_etape}**

## The Numbers
- **Z4/Z5 Time:** {z4_mins + z5_mins}m (Essential Stimulus)
- **Mechanicals:** {cadence} rpm | {hr} bpm avg
- **Pacing (VI):** {vi} | **Climbing:** {elev}m ascent

**Tony's Verdict:** {climb_note} {"Solid pacing. You didn't surge too hard." if vi < 1.06 else "Pacing was surgy. Practice steady power for the long climbs."}

## Recovery Nutrition
- **Target:** 80-100g Carbs + 30g Protein immediately.
"""
    else:
        # Walks, Gym, Pilates
        return f"""
# COACH TONY: {type.upper()} REPORT
**Activity:** {name} | **Load:** {act.get('icu_training_load', 0)} TSS
**Tony's Note:** Structural integrity work. This protects your power on the bike.
"""

def generate_weekly_report(activities, wellness):
    last_7 = activities[-7:]
    total_tss = sum(a.get('icu_training_load', 0) for a in last_7)
    days_to_etape = (ETAPE_DATE - datetime.now()).days
    return f"""
# COACH TONY: WEEKLY STRATEGY
**Total Weekly Load:** {total_tss} TSS
**Fitness (CTL):** {wellness[-1].get('ctl')} | **Form (TSB):** {wellness[-1].get('tsb')}%

**Tony's Note:** {days_to_etape} days to the Etape. Keep the ramp rate sustainable. 8 hours is the goal.
"""

if __name__ == "__main__":
    activities, wellness = get_data()
    now = datetime.now()
    if now.hour == 8:
        report = generate_morning_report(wellness)
    elif now.weekday() == 0 and now.hour == 9:
        report = generate_weekly_report(activities, wellness)
    else:
        report = generate_post_activity_report(activities)

    with open("latest_report.txt", "w") as f:
        f.write(report)
    
    pd.DataFrame(activities).to_csv("activities.csv", index=False)
    pd.DataFrame(wellness).to_csv("wellness.csv", index=False)
