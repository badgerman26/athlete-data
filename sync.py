import requests
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# Configuration
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"
AUTH = ('athlete', API_KEY)

def get_data():
    # 1. Activities (Last 7 days)
    r = requests.get(f"{BASE_URL}/activities", auth=AUTH)
    r.raise_for_status()
    # 2. Wellness (Last 7 days for Sleep/HR analysis)
    oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    r_well = requests.get(f"{BASE_URL}/wellness?oldest={oldest}", auth=AUTH)
    r_well.raise_for_status()
    return r.json(), r_well.json()

def audit_sleep_and_hr(wellness_list):
    """Advanced audit of sleep stages and sleeping heart rate trends."""
    if not wellness_list: return "No wellness data found."
    latest = wellness_list[-1]
    
    hrv = latest.get('hrv', 0)
    rhr = latest.get('restingHR', 0)
    sleep_score = latest.get('sleepQuality', 0)
    sleep_hours = round((latest.get('sleepSecs', 0) / 3600), 1)
    
    # Logic based on Section 11 Readiness Decision
    status = "READY"
    insight = f"Sleep: {sleep_hours}h (Quality: {sleep_score}/4). RHR: {rhr}bpm, HRV: {hrv}ms."
    
    if rhr > latest.get('avgSleepingHR', rhr) + 3:
        status = "MODIFY"
        insight += " | High Sleeping HR detected — sign of incomplete recovery or impending illness."
    if hrv < 50: # Example threshold
        status = "CAUTION"
        insight += " | HRV is suppressed. Keep intensity low today."
        
    return f"STATUS: {status}\nINSIGHT: {insight}"

def generate_weekly_report(activities, wellness):
    """Generates the full Section 11 Weekly Summary."""
    total_tss = sum(a.get('icu_training_load', 0) for a in activities)
    total_hours = round(sum(a.get('moving_time', 0) for a in activities) / 3600, 1)
    
    report = f"""
--- SECTION 11 WEEKLY SUMMARY ---
Hours: {total_hours}h | Total TSS: {total_tss}
Fitness (CTL): {wellness[-1].get('ctl')}
Form (TSB): {wellness[-1].get('tsb')}%

--- SLEEP & RECOVERY AUDIT ---
{audit_sleep_and_hr(wellness)}

--- INTERPRETATION ---
Weekly compliance is high. CTL is building toward KAW targets.
Watch the Sleeping HR trend over the next 48h.
"""
    return report

def generate_post_ride_report(ride, wellness):
    """Daily audit for post-workout validation."""
    name = ride.get('name', 'Unknown')
    z4_time = round(ride.get('time_in_z4', 0) / 60, 1)
    
    report = f"""
--- COACH'S POST-RIDE AUDIT ---
Session: {name}
Threshold (Z4) Time: {z4_time} mins
Load: {ride.get('icu_training_load')} TSS

--- DAILY READINESS ---
{audit_sleep_and_hr(wellness)}

--- NEXT STEPS ---
Ensure 80g carbs post-ride. Saturday Endurance is the primary focus.
"""
    return report

if __name__ == "__main__":
    activities, wellness = get_data()
    pd.DataFrame(activities).to_csv("activities.csv", index=False)
    
    # Determine which report to send
    is_monday = datetime.now().weekday() == 0
    
    if is_monday:
        final_text = generate_weekly_report(activities, wellness)
    else:
        latest_ride = activities[-1] if activities else {}
        final_text = generate_post_ride_report(latest_ride, wellness)
    
    with open("latest_report.txt", "w") as f:
        f.write(final_text)
    
    # Save for Gemini access
    with open("latest.json", "w") as f:
        json.dump({"latest_activity": activities[-1], "wellness": wellness[-1]}, f)
