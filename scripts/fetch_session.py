import hashlib
import json
import os

import dotenv
import requests

dotenv.load_dotenv()
API_KEY = os.environ.get("LASTFM_API_KEY")
SECRET = os.environ.get("LASTFM_SECRET")

if not API_KEY or not SECRET:
    raise ValueError("LASTFM_API_KEY and LASTFM_SECRET must be set in .env file")

auth_token = input("Paste your Last.fm Auth Token: ")

signature = f"api_key{API_KEY}methodauth.getSessiontoken{auth_token}"
signature += SECRET
signature = signature.encode("utf-8")
signature = hashlib.md5(signature).hexdigest()
print(signature)

fetch_session_url = f"https://ws.audioscrobbler.com/2.0/?method=auth.getSession&api_key={API_KEY}&token={auth_token}&api_sig={signature}&format=json"
response = requests.get(fetch_session_url)
if response.status_code != 200:
    print(f"Error: HTTP {response.status_code}")
    print(response.text)
else:
    data = json.loads(response.text)
    print(data)
