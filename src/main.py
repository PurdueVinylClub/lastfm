import random
import requests
import json
import os
import dotenv
import time
import hashlib
import datetime
import sys
import traceback
import socket

featured_album = None
featured_artist = None
featured_member = None
featured_time = None

def get_featured_album() -> (str, str, int):
    pass

def main() -> (bool, str):
    dotenv.load_dotenv()

    API_KEY = os.environ.get('LASTFM_API_KEY')
    SESSION_KEY = os.environ.get('LASTFM_SESSION_KEY')
    SECRET = os.environ.get('LASTFM_SECRET')

    # read members
    
    # if sunday only dues payers
    # TODO (don't have db of dues payers yet)
    with open('usernames.txt', 'r') as f:
        members = f.read().splitlines()

    print_buffer = ""

    # as 09/10 9:45 AM
    print_buffer += time.strftime("%m/%d %I:%M %p", time.localtime()) + " "

    # get random member
    username = random.choice(members)
    print_buffer += username

    # get top albums
    period = "7day"

    topalbums_url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettopalbums&user={username}&api_key={API_KEY}&period={period}&format=json"

    response = requests.get(topalbums_url)
    data = json.loads(response.text)

    if 'topalbums' not in data:
        return False, ""

    top_albums = data['topalbums']['album'][0:15]

    if len(top_albums) == 0:
        return False, ""

    # get random album
    random_album = random.choice(top_albums)

    print_buffer += f" - {random_album['artist']['name']}: {random_album['name']} - "

    albuminfo_url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={API_KEY}&artist={random_album['artist']['name']}&album={random_album['name']}&format=json"

    response = requests.get(albuminfo_url)
    data = json.loads(response.text)

    # download album art
    if 'album' not in data:
        return False, ""

    album_art_url = data['album']['image'][3]['#text']

    if album_art_url != "":
        response = requests.get(album_art_url)
        with open('album_art.jpg', 'wb') as f:
            f.write(response.content)

    if 'tracks' in data['album']:
        if 'track' not in data['album']['tracks'] or not data['album']['tracks']['track']:
            return False, ""

        time_now = int(time.time())

        # print random track
        random_track = random.choice(list(data['album']['tracks']['track']))
        scrobble_sig = ""
        if 'name' in random_track:
            track_name = random_track['name']
        elif random_track is str:
            track_name = random_track
        else:
            return False, ""

        print_buffer += " " + track_name
        scrobble_sig += f"api_key{API_KEY}artist{random_album['artist']['name']}methodtrack.scrobblesk{SESSION_KEY}timestamp{time_now}track{track_name}"

        # construct sig to scrobble track
        scrobble_sig += SECRET
        scrobble_sig = scrobble_sig.encode('utf-8')
        scrobble_sig = hashlib.md5(scrobble_sig).hexdigest()

        # scrobble track
        scrobble_url = f"http://ws.audioscrobbler.com/2.0/"
        post_body = {
            'method': 'track.scrobble',
            'api_key': API_KEY,
            'artist': random_album['artist']['name'],
            'track': track_name,
            'timestamp': time_now,
            'sk': SESSION_KEY,
            'api_sig': scrobble_sig,
            'format': 'json'
        }
        response = requests.post(scrobble_url, data=post_body)
        data = json.loads(response.text)
        print_buffer += " " + str(data)

    return True, print_buffer

if __name__ == "__main__":
    while True:
        try:
            (success, print_buffer) = main()
            if success:
                print(print_buffer)
                break
        except (ConnectionError, socket.gaierror) as e:
            # no use continuously retrying, seems like deeper (network) issue
            print(f"{time.strftime('%m/%d %I:%M %p')} ConnectionError/socket.gaierror: {str(e)}, aborting...", file=sys.stderr)
            break
        except Exception as e:
            tb = traceback.format_exc()
            print(f"{time.strftime('%m/%d %I:%M %p')} Error: {str(tb)}", file=sys.stderr)
            # try again
            continue