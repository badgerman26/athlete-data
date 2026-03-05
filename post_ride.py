import requests
import os
from datetime import datetime

# --- CONFIG ---
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('API_KEY', KEY) 
KAW_DATE = datetime(2026, 5, 15)
ETAPE_DATE = datetime(2026, 7, 19)

def get_latest_activity():
    # Grab just the absolute latest activity
    url = "https://intervals.icu/api/v1/athlete/0/activities?limit=1"
    try:
        r = requests.get(url, auth=AUTH)
        return r.json()[0] if r.status_code == 200 and len(r.json()) > 0 else None
    except: return None

def safe_num(val, default=0.0):
    try: return float(val) if val is not None else default
    except: return default

if __name__ == "__main__":
    latest = get_latest_activity()
    
    if latest:
        # 1. Identity
        act_name = latest.get('name', 'Unknown Session')
        act_type = latest.get('type', 'Activity')
        
        # 2. Core Metrics
        dist_mi = round(safe_num(latest.get('distance')) / 1609.34, 1)
        elev_m = int(safe_num(latest.get('total_elevation_gain')))
        time_mins = int(safe_num(latest.get('moving_time')) / 60)
        
        # 3. Pro Power Metrics
        np = safe_num(latest.get('icu_weighted_average_power'))
        if_ = safe_num(latest.get('icu_intensity_factor'))
        load = int(safe_num(latest.get('icu_training_load')))
        kj = int(safe_num(latest.get('calories')))
        drift = safe_num(latest.get('icu_pw_hr'))
        
        # 4. Premium AI Calculations
        # Estimated Carb Burn (Grams): Higher intensity burns a higher % of carbs.
        # 1g Carb = ~4 kcal. We use (kJ * IF) / 4 as a rough sports-science heuristic.
        estimated_carbs = int((kj * if_) / 4) if kj > 0 else 0
        
        # Execution Grading Logic
        if act_type not in ['Ride', 'VirtualRide', 'GravelRide', 'EBikeRide']:
            grade = "Active Recovery / Cross-Training"
            verdict = f"Good off-bike work. {load} TSS added to the bank."
        else:
            if if_ < 0.75 and drift < 5.0:
                grade = "🟢 Perfect Endurance (Zone 2 Masterclass)"
                verdict = f"Flawless execution. You kept the intensity low and the heart rate steady. This builds the exact fat-burning engine you need for Day 3 of KAW."
            elif if_ > 0.85:
                grade = "🔴 High-Intensity Breakthrough"
                verdict = f"You opened the taps today! Massive {load} TSS effort. Make sure you clear the lactic acid because tomorrow MUST be an easy day or a rest day."
            elif if_ >= 0.75 and if_ <= 0.85 and time_mins > 60:
                grade = "🟡 The Grey Zone Warning"
                verdict = f"Intensity Factor was {if_}. This is 'Tempo' or the Grey Zone. It feels hard, but doesn't trigger the high-end adaptations of Z4, and causes too much fatigue for pure base building. Unless this was a specific sweet-spot workout, polarize your training more!"
            else:
                grade = "🔵 Solid Maintenance Effort"
                verdict = "Good honest miles. Keep stacking these up."

        # --- DYNAMIC REPORT ---
        report = f"""# 🏁 COACH TONY: POST-RIDE DEBRIEF
**Session:** {act_name} ({act_type})
**Time:** {time_mins} mins | **Distance:** {dist_mi} mi | **Climbing:** {elev_m}m

## 🧠 AI Execution Analysis
- **Execution Grade:** {grade}
- **Normalized Power:** {int(np)}W | **Intensity Factor:** {if_}
- **Aerobic Drift:** {drift}% {"(Highly Efficient)" if drift < 5 and drift > 0 else "(Heart rate creeping up - stamina limit reached)"}

## ⛽ Fueling & Recovery Audit
- **Work Completed:** {kj} kJ
- **Estimated Carbs Burned:** ~{estimated_carbs}g
- **Session Load (TSS):** {load}

**Tony's Verdict:** {verdict}

**Next Step:** You burned roughly {estimated_carbs}g of glycogen. If you didn't eat that on the bike, your recovery window is open right now. Go eat some carbs before your muscles realize they are empty.

*(KAW: {(KAW_DATE - datetime.now()).days} Days | L'Etape: {(ETAPE_DATE - datetime.now()).days} Days)*
"""
    else:
        report = "# COACH TONY: WAITING FOR GPS DATA..."

    with open("latest_report.txt", "w") as f:
        f.write(report)
