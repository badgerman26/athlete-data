import requests
import os
from datetime import datetime, timedelta

# --- CONFIG ---
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('API_KEY', KEY) 
KAW_DATE = datetime(2026, 5, 15)
ETAPE_DATE = datetime(2026, 7, 19)

def get_weekly_data(endpoint="activities"):
    # Pull the last 7 days
    oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = f"https://intervals.icu/api/v1/athlete/0/{endpoint}?oldest={oldest}"
    try:
        r = requests.get(url, auth=AUTH)
        return r.json() if r.status_code == 200 else []
    except: return []

def safe_num(val, default=0.0):
    try: return float(val) if val is not None else default
    except: return default

if __name__ == "__main__":
    activities = get_weekly_data("activities")
    wellness = get_weekly_data("wellness")
    
    # --- WEEKLY AGGREGATION ---
    total_miles = 0.0
    total_elev = 0
    total_tss = 0
    total_kj = 0
    z1_z2_mins = 0
    z3_mins = 0
    z4_z5_mins = 0
    peak_w_kg = 0.0
    
    # Get current weight from the latest wellness entry (fallback to 75kg)
    current_weight = safe_num(wellness[-1].get('weight') if wellness else 75.0, 75.0)

    for act in activities:
        if act.get('type') in ['Ride', 'VirtualRide', 'GravelRide', 'EBikeRide']:
            total_miles += safe_num(act.get('distance')) / 1609.34
            total_elev += safe_num(act.get('total_elevation_gain'))
            total_tss += safe_num(act.get('icu_training_load'))
            total_kj += safe_num(act.get('calories'))
            
            # Tally Time in Zones (seconds to minutes)
            z1_z2_mins += safe_num(act.get('time_in_z1', 0)) + safe_num(act.get('time_in_z2', 0))
            z3_mins += safe_num(act.get('time_in_z3', 0))
            z4_z5_mins += safe_num(act.get('time_in_z4', 0)) + safe_num(act.get('time_in_z5', 0)) + safe_num(act.get('time_in_z6', 0))
            
            # Find the best W/kg performance of the week
            np = safe_num(act.get('icu_weighted_average_power'))
            act_w_kg = np / current_weight if current_weight > 0 else 0
            if act_w_kg > peak_w_kg:
                peak_w_kg = act_w_kg

    # Convert zone minutes to percentages for Polarized Audit
    total_zone_mins = z1_z2_mins + z3_mins + z4_z5_mins
    if total_zone_mins > 0:
        p_z1_z2 = (z1_z2_mins / total_zone_mins) * 100
        p_z3 = (z3_mins / total_zone_mins) * 100
        p_z4_z5 = (z4_z5_mins / total_zone_mins) * 100
    else:
        p_z1_z2 = p_z3 = p_z4_z5 = 0

    # --- THE ETAPE SIMULATOR ---
    # A rough Alpine physics heuristic: 
    # For a massive 4000m+ day, 2.5 W/kg = ~9.5 hrs. 3.0 W/kg = ~8.5 hrs. 3.5 W/kg = ~7.5 hrs.
    if peak_w_kg > 0:
        simulated_hours = max(5.0, 12.0 - (1.25 * peak_w_kg)) 
        etape_pred = f"{int(simulated_hours)}h {int((simulated_hours % 1) * 60)}m"
    else:
        etape_pred = "Insufficient Power Data"

    # --- AI DIRECTOR SPORTIF LOGIC ---
    if total_miles == 0:
        verdict = "You didn't ride this week. If you were sick or resting, good. If you were busy, you need to find time. KAW is coming."
    elif p_z3 > 40:
        verdict = f"🔴 GREY ZONE WARNING: You spent {p_z3:.0f}% of your time in Zone 3 (Tempo). This is 'junk mile' territory. It makes you tired without pushing your FTP up or building your aerobic base. Next week, ride your easy days EASIER, and your hard days HARDER."
    elif total_tss < 300:
        verdict = "🟡 LOW VOLUME: A total weekly TSS of under 300 is maintenance mode. To survive 3 days of KAW, we need to push this up to 400-500 TSS per week safely."
    else:
        verdict = f"🟢 EXCELLENT EXECUTION: {total_tss:.0f} TSS this week. You built serious resilience. Rest up today, because next week we go again."

    # --- DYNAMIC REPORT ---
    report = f"""# 📊 COACH TONY: SUNDAY STRATEGY REVIEW
**Week Ending:** {datetime.now().strftime("%B %d, %Y")}

## 🏔️ The L'Etape Simulator
- **Current Peak W/kg:** {peak_w_kg:.2f}
- **Predicted Etape Finish Time:** {etape_pred}
- *(To shave 30 minutes off this time, you need to find another 0.4 W/kg before July!)*

## ⛺ King Alfred's Way (KAW) Durability Audit
- **Weekly Volume:** {total_miles:.1f} miles | {total_elev:.0f}m ascent
- **Total Work Done:** {total_kj:.0f} kJ 
- **Cumulative Load (TSS):** {total_tss:.0f}
- *(KAW Day 1 alone will be ~250 TSS. Is your weekly volume high enough to handle three of those in a row?)*

## 🔬 Polarized Training Audit (The 80/20 Rule)
- **Zone 1/2 (Endurance Base):** {p_z1_z2:.0f}% *(Target: ~80%)*
- **Zone 3 (The Grey Zone):** {p_z3:.0f}% *(Target: <10%)*
- **Zone 4/5+ (Threshold/VO2):** {p_z4_z5:.0f}% *(Target: ~10-15%)*

**Director Sportif Verdict:**
{verdict}

Enjoy your Sunday evening. Get your kit ready for tomorrow. 
*(KAW: {(KAW_DATE - datetime.now()).days} Days | L'Etape: {(ETAPE_DATE - datetime.now()).days} Days)*
"""

    with open("weekly_report.txt", "w") as f:
        f.write(report)
