import requests
import os

# --- CONFIG ---
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', KEY)

def find_me():
    # This is the standard 'Me' endpoint for many APIs including Intervals
    url = "https://intervals.icu/api/v1/me"
    
    try:
        print("Knocking on the door...")
        r = requests.get(url, auth=AUTH)
        
        if r.status_code == 200:
            me = r.json()
            athlete_id = me.get('id')
            name = me.get('name')
            return f"SUCCESS! You are {name}. Your ACTUAL ID is: {athlete_id}"
        
        elif r.status_code == 404:
            # Fallback if /me isn't supported, try the profile endpoint
            print("Fallback to profile endpoint...")
            r2 = requests.get("https://intervals.icu/api/v1/athlete/profile", auth=AUTH)
            if r2.status_code == 200:
                me = r2.json()
                return f"SUCCESS! You are {me.get('name')}. Your ACTUAL ID is: {me.get('id')}"
            else:
                return f"FAILED: Even the fallback failed with status {r2.status_code}."
        
        else:
            return f"FAILED: Status {r.status_code}. If it's 401, re-copy the API Key."
            
    except Exception as e:
        return f"CRASH: {str(e)}"

if __name__ == "__main__":
    result = find_me()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
