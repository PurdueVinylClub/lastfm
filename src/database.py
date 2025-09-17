import json
import csv

def set_featured_album(discord_id: int, lastfm_user: str, artist_name: str, artist_url: str, album: str, album_url: str, timestamp: int, cover_url: str) -> bool:
    album = dict({
        'member_d': discord_id, # discord id
        'member_l': lastfm_user, # lastfm username
        'artist_name': artist_name, # artist name
        'artist_url': artist_url, # artist url
        'album': album, # album name
        'album_url': album_url, # album url
        'timestamp': timestamp, # timestamp
        'cover_url': cover_url # cover url
    })

    fieldnames = album.keys()
    with open('featured.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(album)

    return True

def get_featured_album() -> dict:
    # read from csv
    with open('featured.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        return reader[1]

def get_lastfm_user(discord_id: int) -> str:
    pass

def get_discord_id(lastfm_user: str) -> int:
    pass

def get_featured_log(lastfm_user: str) -> list[dict]:
    with open(f"usernames/{lastfm_user}.log", 'r') as f:
        featured_log = f.read().splitlines()
    
    # TODO
    pass

def get_preferences(discord_id: int) -> dict:
    pass

# pass/fail
def set_lfm_discord_connection(discord_id: int, lastfm_user: str) -> bool:
    pass

# pass/fail
def set_preferences(discord_id: int, preferences: dict):
    pass
