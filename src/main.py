import datetime
import hashlib
import json
import os
import random
import socket
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote_plus

import dotenv
import requests
import urllib3

import database as db

# Get data directory from environment or use default
DATA_DIR = Path(os.environ.get("PVC_DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True)


def main() -> tuple[dict | None, str]:
    """Main function to feature an album and scrobble a track."""
    db.init()  # connect to database (if not already)
    dotenv.load_dotenv()

    API_KEY = os.environ.get("LASTFM_API_KEY")
    SESSION_KEY = os.environ.get("LASTFM_SESSION_KEY")
    SECRET = os.environ.get("LASTFM_SECRET")

    if API_KEY is None or SESSION_KEY is None or SECRET is None:
        print("Error: Missing API credentials", file=sys.stderr)
        return None, ""

    print_buffer = ""

    # such as 09/10 9:45 AM
    print_buffer += time.strftime("%m/%d %I:%M %p", time.localtime()) + " "

    # on sundays, special users (dues payers) are pulled twice as often
    # but non-special users are still in the lottery pool
    is_sunday = datetime.datetime.now().weekday() == 6
    username = db.get_random_user(double_special_chance=is_sunday)
    if username is None:
        print("Error: No users found in database", file=sys.stderr)
        return None, ""

    print_buffer += username

    # get top albums
    period = "7day"

    topalbums_url = f"https://ws.audioscrobbler.com/2.0/?method=user.gettopalbums&user={quote_plus(username)}&api_key={API_KEY}&period={period}&format=json"

    response = requests.get(topalbums_url)
    if response.status_code != 200:
        print(f"Error fetching top albums: HTTP {response.status_code}", file=sys.stderr)
        return None, ""
    data = json.loads(response.text)

    if "topalbums" not in data:
        print(f"Error: No topalbums in response: {data}", file=sys.stderr)
        return None, ""

    if "album" not in data["topalbums"] or not isinstance(data["topalbums"]["album"], list):
        print("Error: No albums found in API response", file=sys.stderr)
        return None, ""

    top_albums = data["topalbums"]["album"][0:15]

    if len(top_albums) == 0:
        print("Error: User has no top albums", file=sys.stderr)
        return None, ""

    # get random album
    random_album = random.choice(top_albums)

    # Validate album structure
    if (
        not isinstance(random_album, dict)
        or "artist" not in random_album
        or "name" not in random_album
    ):
        print("Error: Invalid album structure in API response", file=sys.stderr)
        return None, ""

    if not isinstance(random_album["artist"], dict) or "name" not in random_album["artist"]:
        print("Error: Invalid artist structure in API response", file=sys.stderr)
        return None, ""

    print_buffer += f" - {random_album['artist']['name']}: {random_album['name']} - "

    albuminfo_url = f"https://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={API_KEY}&artist={quote_plus(random_album['artist']['name'])}&album={quote_plus(random_album['name'])}&format=json"

    response = requests.get(albuminfo_url)
    if response.status_code != 200:
        print(f"Error fetching album info: HTTP {response.status_code}", file=sys.stderr)
        return None, ""
    data = json.loads(response.text)

    # download album art
    if "album" not in data:
        print(f"Error: No album info in response: {data}", file=sys.stderr)
        return None, ""

    # Try to get the largest image (usually index 3), fallback to smaller if not available
    album_art_url = ""
    if (
        "image" in data["album"]
        and isinstance(data["album"]["image"], list)
        and len(data["album"]["image"]) > 0
    ):
        # Try to get the largest image (index 3), or the last available one
        image_list = data["album"]["image"]
        if len(image_list) > 3 and "#text" in image_list[3]:
            album_art_url = image_list[3]["#text"]
        elif "#text" in image_list[-1]:
            album_art_url = image_list[-1]["#text"]

    if album_art_url and album_art_url != "":
        response = requests.get(album_art_url)
        if response.status_code == 200:
            album_art_path = DATA_DIR / "album_art.jpg"
            with open(album_art_path, "wb") as f:
                f.write(response.content)
        else:
            print(
                f"Warning: Failed to download album art: HTTP {response.status_code}",
                file=sys.stderr,
            )

    if "tracks" in data["album"]:
        if "track" not in data["album"]["tracks"] or not data["album"]["tracks"]["track"]:
            print("Error: Album has no tracks", file=sys.stderr)
            return None, ""

        time_now = int(time.time())

        # print random track
        random_track = random.choice(list(data["album"]["tracks"]["track"]))
        scrobble_sig = ""
        if "name" in random_track:
            track_name: str = random_track["name"]
        elif isinstance(random_track, str):
            track_name = random_track
        else:
            print(f"Error: Invalid track format: {random_track}", file=sys.stderr)
            return None, ""

        print_buffer += f" {track_name}"
        scrobble_sig += f"api_key{API_KEY}artist{random_album['artist']['name']}methodtrack.scrobblesk{SESSION_KEY}timestamp{time_now}track{track_name}"

        # construct sig to scrobble track
        scrobble_sig += SECRET
        scrobble_sig = scrobble_sig.encode("utf-8")
        scrobble_sig = hashlib.md5(scrobble_sig).hexdigest()

        # scrobble track
        scrobble_url = "https://ws.audioscrobbler.com/2.0/"
        post_body = {
            "method": "track.scrobble",
            "api_key": API_KEY,
            "artist": random_album["artist"]["name"],
            "track": track_name,
            "timestamp": time_now,
            "sk": SESSION_KEY,
            "api_sig": scrobble_sig,
            "format": "json",
        }
        response = requests.post(scrobble_url, data=post_body)
        if response.status_code != 200:
            print(
                f"Warning: Failed to scrobble track: HTTP {response.status_code}: {response.text}",
                file=sys.stderr,
            )
        else:
            data = json.loads(response.text)
            print_buffer += " " + str(data)

    featured_album = {
        "member_l": username,
        "artist_name": random_album["artist"]["name"],
        "artist_url": random_album["artist"]["url"],
        "album": random_album["name"],
        "album_url": random_album["url"],
        "cover_url": album_art_url,
    }

    return featured_album, print_buffer


if __name__ == "__main__":
    MAX_RETRIES = 3
    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            (featured_album, print_buffer) = main()
            if featured_album:
                print(print_buffer)
                db.set_featured_album(
                    featured_album["member_l"],
                    featured_album["artist_name"],
                    featured_album["artist_url"],
                    featured_album["album"],
                    featured_album["album_url"],
                    featured_album["cover_url"],
                )
                break
            else:
                # main() returned None, likely due to API error or no data
                print(
                    f"{time.strftime('%m/%d %I:%M %p')} No album featured (returned None)",
                    file=sys.stderr,
                )
                break
        except (
            ConnectionError,
            socket.gaierror,
            urllib3.exceptions.NameResolutionError,
        ) as e:
            # no use continuously retrying, seems like deeper (network) issue
            print(
                f"{time.strftime('%m/%d %I:%M %p')} ConnectionError/socket.gaierror: {str(e)}, aborting...",
                file=sys.stderr,
            )
            break
        except (requests.RequestException, json.JSONDecodeError) as e:
            # Retryable errors
            retry_count += 1
            print(
                f"{time.strftime('%m/%d %I:%M %p')} Request/JSON error (attempt {retry_count}/{MAX_RETRIES}): {str(e)}",
                file=sys.stderr,
            )
            if retry_count >= MAX_RETRIES:
                print(
                    f"{time.strftime('%m/%d %I:%M %p')} Max retries reached, aborting...",
                    file=sys.stderr,
                )
                break
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            # Unexpected errors - don't retry
            tb = traceback.format_exc()
            print(
                f"{time.strftime('%m/%d %I:%M %p')} Unexpected error: {str(e)}\n{tb}",
                file=sys.stderr,
            )
            break
