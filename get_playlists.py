from os import mkdir
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path
from dotenv import load_dotenv
import shutil
import os
import os.path
import re

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8888/callback')
USER = os.getenv('USER')
SYNC_FOLDER = os.getenv('SYNC_FOLDER', './playlists')

SCOPE= 'playlist-read-collaborative' 
REMOVE = False

EXISTING_PLAYLISTS = os.listdir(SYNC_FOLDER) if os.path.exists(SYNC_FOLDER) else []

def authenticate():
    '''
    Authenticate Spotify api
    '''
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE))
    return sp

def get_playlists(sp, user=USER):
    '''
    fetch playlists names from Spotify
    '''
    playlists = {}
    results = sp.user_playlists(user=user)
    for entry in results["items"]:
        playlist_name = re.sub(r"[^A-Za-z0-9]", "", entry["name"]) #remove wihtespaces and stuff
        playlists[playlist_name] = entry["external_urls"]["spotify"]
    return playlists

def sync_single_playlist(url, name):
    '''
    Use spodl to sync a single playlist 
    '''
    command = f"spotdl sync {url} --save-file {name}.sync.spotdl"
    print("run: ", command)
    os.system(command)

def sync_playlists(playlists, sync_folder=SYNC_FOLDER):
    '''
    create playlist classes for each playlist
    '''
    for name, url in playlists.items():
        os.chdir(SYNC_FOLDER)
        Path(name).mkdir(parents=True, exist_ok=True)
        os.chdir(os.path.join(SYNC_FOLDER, name))
        sync_single_playlist(url, name)


#TODO: "Implement removing not wanted playlists"
def fetch_playlists_to_remove(playlists, existing_playlists=set(EXISTING_PLAYLISTS)):
    playlist_names = set(playlists.keys())
    playlists_to_remove = existing_playlists.difference(playlist_names)
    return playlists_to_remove

def remove_deleted_playlists(playlists_to_remove):
    for name in playlists_to_remove:
        f = os.path.join(SYNC_FOLDER, name)

        if os.path.isdir(f):
            if input("Remove the playlist: ", name):
                shutil.rmtree(f)
    return

