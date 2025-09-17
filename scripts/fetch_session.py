import requests
import json
import os
import dotenv
import hashlib

dotenv.load_dotenv()
API_KEY = os.environ.get('LASTFM_API_KEY')
SECRET = os.environ.get('LASTFM_SECRET')

auth_token = input("Paste your Last.fm Auth Token: ")

signature = f"api_key{API_KEY}methodauth.getSessiontoken{auth_token}"
signature += SECRET
signature = signature.encode('utf-8')
signature = hashlib.md5(signature).hexdigest()
print(signature)

fetch_session_url = f"http://ws.audioscrobbler.com/2.0/?method=auth.getSession&api_key={API_KEY}&token={auth_token}&api_sig={signature}&format=json"
response = requests.get(fetch_session_url)
data = json.loads(response.text)
print(data)