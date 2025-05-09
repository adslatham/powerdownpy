print ("Starting imports")

import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os

print("Starting script execution")

# Set up Chrome options for headless run
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

# Create the webdriver
driver = webdriver.Chrome(options=options)

# Load environment variables
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SPOTIPY_REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
PLAYLIST_ID = os.getenv("POWERDOWN_PLAYLIST_ID")
USERNAME = os.getenv("SPOTIPY_USERNAME")

driver.get("https://www.bbc.co.uk/sounds/brand/p04m6srg")

print ("Waiting for 2 seconds")

time.sleep(2)

print ("Done waiting")

def clean_title(title):
    return re.sub(r"\(feat\..*?\)", "", title, flags=re.IGNORECASE).strip()

def search_song(sp, artist, title):
    cleaned_title = clean_title(title)
    query = f"track:{cleaned_title} artist:{artist}"
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    #print (tracks[0]["id"] if tracks else "No Track Found")
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
        for i in range(0, len(tracks), 100):
            sp.playlist_remove_all_occurrences_of_items(playlist_id, tracks[i:i+100])
        print(f"✅ Cleared {len(tracks)} tracks from playlist.")

def add_songs_to_playlist(sp, playlist_id, track_ids):
    for i in range(0, len(track_ids), 100):
        sp.playlist_add_items(playlist_id, track_ids[i:i+100])
    print(f"✅ {len(track_ids)} tracks added to playlist.")

soup = BeautifulSoup(driver.page_source, "html.parser")
divs = soup.find_all("div", attrs={"data-testid": "playableListCard"})

links = []
for div in divs:
    a_tag = div.find("a", href=True)
    if a_tag:
        links.append(a_tag["href"])

songs = []

for link in links:
    print(link)
    
    driver.get("https://www.bbc.co.uk" + link)
    driver.implicitly_wait(2)
    soundshtml = driver.page_source
    
    showsoup = BeautifulSoup(soundshtml, "html.parser")
    i = 0
    for tile in showsoup.select(".sc-c-basic-tile"):
        artist = tile.select_one(".sc-c-basic-tile__artist")
        title = tile.select_one(".sc-c-basic-tile__title")
        if artist and title:
            song_tuple = (artist.text.strip(), title.text.strip())
            if song_tuple not in songs:
                songs.append(song_tuple)
                i+=1
    print(str(i) + " new songs added to array")

driver.quit()

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

print ("Power Down Playlist generation complete")
