from os import mkdir
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path
from config import *
import shutil

SCOPE = "user-library-read"
REMOVE = False

EXISTING_PLAYLISTS = os.listdir(SYNC_FOLDER)

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
def sync_playlists(playlists, sync_folder= SYNC_FOLDER):
     for name, url in playlists.items():
          os.chdir(SYNC_FOLDER)
          Path(name).mkdir(parents=True, exist_ok=True)
          os.chdir(os.path.join(SYNC_FOLDER, name ))
          sync_playlist(url, name)
     
def fetch_playlists_to_remove(playlists , existing_playlists = set(EXISTING_PLAYLISTS)):
     playlist_names = set(playlists.keys())
     playlists_to_remove = existing_playlists.difference(playlist_names)
    
     return playlists_to_remove

def remove_deleted_playlists(playlists_to_remove):
     for name in playlists_to_remove:
          f = os.path.join(SYNC_FOLDER, name)
          
          if  os.path.isdir(f):
               if input("Remove the playlist: ", name ):
                    shutil.rmtree(f)
     return 

def main():
     # change directory to current working directory
     os.chdir(SYNC_FOLDER)
     
     # authenticate user with config file
     sp = authenticate()

     # get all playlists from user
     playlists = get_playlists(sp)

     # remove delted playlists

     if REMOVE:
          playlists_to_remove = fetch_playlists_to_remove(playlists)
          remove_deleted_playlists(playlists_to_remove)

     # download or sync playlists
     sync_playlists(playlists)

main()

