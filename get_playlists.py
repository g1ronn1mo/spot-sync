from os import mkdir
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path
from config import *

SCOPE = "user-library-read"

# authenticate
def authenticate():
     sp = spotipy.Spotify(auth_manager=SpotifyOAuth( \
          client_id=CLIENT_ID, \
          client_secret=CLIENT_SECRET,\
          redirect_uri=REDIRECT_URI,\
          scope=SCOPE))
     return sp

def get_playlists(sp, user=USER):
     playlists= {}
     results = sp.user_playlists(user=user)

     for entry in results["items"]:
          playlists[entry["name"]] = entry["external_urls"]["spotify"]
     return playlists     


def sync_playlist(url, name):
     command = "spotdl sync " + url
     os.system(command)


# create playlist classes for each playlist
def download_playlists(playlists, sync_folder= SYNC_FOLDER):
     for name, url in playlists.items():
          os.chdir(SYNC_FOLDER)
          Path(name).mkdir(parents=True, exist_ok=True)
          os.chdir(os.path.join(SYNC_FOLDER, name ))
          sync_playlist(url, name)
     
def remove_deleted_playlists():
     pass

def main():
     os.chdir(SYNC_FOLDER)
     sp = authenticate()
     playlists = get_playlists(sp)
     download_playlists(playlists)

main()