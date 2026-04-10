# -*- coding: utf-8 -*-
import urllib.request
import os

print("1. Downloading fresh v3.92 engine from GitHub...")
url = "https://raw.githubusercontent.com/CrankAddict/section-11/main/examples/sync.py"
response = urllib.request.urlopen(url)
code = response.read().decode('utf-8')

print("2. Injecting L'Etape Watts/kg tracking...")
code = code.replace(
    '"w_prime": power_model.get("w_prime"),',
    '"w_kg": round(power_model.get("eftp") / (latest_wellness.get("weight") or athlete.get("icu_weight")), 2) if power_model.get("eftp") and (latest_wellness.get("weight") or athlete.get("icu_weight")) else None,\n                    "w_prime": power_model.get("w_prime"),'
)

print("3. Routing Garmin Sleeping HR into Baselines...")
code = code.replace(
    'w.get("restingHR")', 
    '(w.get("avgSleepingHR") or w.get("restingHR"))'
)

print("4. Adjusting TSB Fatigue thresholds to -40 for Build Phase...")
code = code.replace('"tsb_amber": -30', '"tsb_amber": -40')
code = code.replace('if tsb < -30:', 'if tsb < -40:')

print("5. Saving fully tuned engine to sync.py...")
with open("sync.py", "w", encoding="utf-8") as f:
    f.write(code)

print("\nSUCCESS! Your engine is fully upgraded to v3.92.")