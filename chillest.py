print ("Starting imports")

import re
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import requests
import json

print("Starting script execution")


url = "https://www.bbc.co.uk/sounds/brand/b03hjfww"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("Page retrieved successfully.")
    #print(response.text)  # print first 1000 characters of the HTML
else:
    print(f"Failed to retrieve page. Status code: {response.status_code}")

# Load environment variables
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SPOTIPY_REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
PLAYLIST_ID = os.getenv("CHILLEST_PLAYLIST_ID")
USERNAME = os.getenv("SPOTIPY_USERNAME")

html = response.text

def clean_title(title):
    """Remove '(feat. ...)' or similar from the title."""
    return re.sub(r"\(feat\..*?\)", "", title, flags=re.IGNORECASE).strip()
    
def search_song(sp, artist, title):
    """Search for a song on Spotify using a cleaned title."""
    cleaned_title = clean_title(title)
    query = f"track:{cleaned_title} artist:{artist}"
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    return tracks[0]["id"] if tracks else None

def get_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    while results:
        tracks.extend([track["track"]["id"] for track in results["items"]])
        results = sp.next(results) if results["next"] else None
    return tracks

def clear_playlist(playlist_id):
    tracks = get_playlist_tracks(playlist_id)
    if tracks:
        # Spotify allows removing max 100 tracks per request
        for i in range(0, len(tracks), 100):
            sp.playlist_remove_all_occurrences_of_items(playlist_id, tracks[i:i+100])
        print(f"✅ Cleared {len(tracks)} tracks from playlist.")
   
def add_songs_to_playlist(sp, playlist_id, track_ids):
    for i in range(0, len(track_ids), 100):
        sp.playlist_add_items(playlist_id, track_ids[i:i+100])
    print(f"✅ {len(track_ids)} tracks added to playlist.")

def add_songs_to_existing_playlist(sp, playlist_id, track_ids):
    existing_tracks = get_existing_tracks(sp, playlist_id)
    new_tracks = [tid for tid in track_ids if tid and tid not in existing_tracks]

    if new_tracks:
        sp.playlist_add_items(playlist_id, new_tracks, position=0)
        print(f"Added {len(new_tracks)} new songs to the playlist.")
    else:
        print("No new songs to add.")  

soup = BeautifulSoup(html, "html.parser")

divs = soup.find_all("a", attrs={"data-bbc-container": "list-tleo"})

print("cards:" + str(len(divs)))

links = []
for div in divs:
    links.append(div["href"])

songs = []
l = 0
for link in links:
    if l < 4:
        
        print(link)
        
        url = "https://www.bbc.co.uk" + link
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print("Page retrieved successfully.")
            #print(response.text)
        else:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
                        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            tracklist = []

            # Find all script tags
            scripts = soup.find_all("script")

            preloaded_state = None

            # Search for the one containing '__PRELOADED_STATE__'
            for script in scripts:
                if script.string and "__PRELOADED_STATE__" in script.string:
                    match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?})\s*;', script.string, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                        try:
                            preloaded_state = json.loads(json_str)
                            print("Parsed __PRELOADED_STATE__ successfully.")
                            tracklist = preloaded_state["tracklist"]["tracks"]
                            
                            i = 0
                            for t in tracklist:
                                artist = t["titles"]["primary"]
                                title = t["titles"]["secondary"]
                                if artist and title:
                                    song_tuple = (artist.strip(), title.strip())
                                    if song_tuple not in songs:
                                        songs.append(song_tuple)
                                        i+=1
                            print(str(i) + " new songs added to array")
                        except json.JSONDecodeError as e:
                            print("Failed to decode JSON:", e)
                    break

            if preloaded_state is None:
                print("__PRELOADED_STATE__ not found.")
        else:
            print(f"Request failed. Status code: {response.status_code}")
    l+=1

print(songs)

# Get a fresh access token using the refresh token
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="playlist-modify-public",
)

print("Refreshing access token...")
token_info = sp_oauth.refresh_access_token(SPOTIPY_REFRESH_TOKEN)
access_token = token_info['access_token']
print("Access token refreshed")

# Set up Spotipy with the access token
sp = spotipy.Spotify(auth=access_token)

track_ids = [search_song(sp, artist, title) for artist, title in songs]
track_ids = [tid for tid in track_ids if tid]

print (track_ids)

clear_playlist(PLAYLIST_ID)
add_songs_to_playlist(sp, PLAYLIST_ID, track_ids)

print ("Chillest Show Playlist generation complete")
