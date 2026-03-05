import requests
import os

# --- CONFIG ---
# This pulls the secrets you saved in GitHub
ATHLETE_ID = os.environ.get('INTERVALS_ID')
API_KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', API_KEY)

def nuclear_debug():
    print("--- STARTING NUCLEAR DEBUG ---")
    
    # 1. Test the 'WHOAMI' endpoint (This doesn't need an ID)
    # This confirms if the API Key is actually valid for ANYONE.
    print("Checking API Key validity...")
    res = requests.get("https://intervals.icu/api/v1/athlete", auth=AUTH)
    
    if res.status_code == 200:
        me = res.json()
        print(f"SUCCESS: API Key is valid for Athlete: {me.get('name')} (ID: {me.get('id')})")
        
        # Now compare what the API says vs what you put in GitHub
        if str(me.get('id')) != str(ATHLETE_ID):
            return f"MATCH ERROR: Your Secret ID is {ATHLETE_ID}, but your API Key belongs to ID {me.get('id')}. Update GitHub Secret to {me.get('id')}."
        else:
            return f"ID MATCHES! Key is good for {me.get('name')}. If you still get 403 on activities, it's a server-side permission issue."
            
    elif res.status_code == 401:
        return "ERROR 401: The API Key itself is wrong. Re-copy it from Intervals.icu Settings."
    elif res.status_code == 403:
        return f"ERROR 403: The API Key is recognized, but it is explicitly forbidden from seeing Athlete {ATHLETE_ID}."
    else:
        return f"UNKNOWN ERROR: Status {res.status_code}"

if __name__ == "__main__":
    result = nuclear_debug()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
