import requests
import os

# --- CONFIG ---
KEY = os.environ.get('INTERVALS_API_KEY')
AUTH = ('athlete', KEY)

def the_final_test():
    # This endpoint tells us who the key belongs to without needing an ID
    url = "https://intervals.icu/api/v1/athlete"
    
    try:
        print("Connecting to Intervals.icu to find your true ID...")
        r = requests.get(url, auth=AUTH)
        
        if r.status_code == 200:
            me = r.json()
            athlete_id = me.get('id')
            name = me.get('name')
            return f"SUCCESS! The Key works. You are {name}. Your ACTUAL ID is: {athlete_id}"
        
        elif r.status_code == 401:
            return "ERROR 401: The API Key itself is wrong. Re-copy it from Intervals.icu Settings."
        
        else:
            return f"FAILED: Status {r.status_code}. The server rejected the request."
            
    except Exception as e:
        return f"CRASH: {str(e)}"

if __name__ == "__main__":
    result = the_final_test()
    print(result)
    with open("latest_report.txt", "w") as f:
        f.write(result)
