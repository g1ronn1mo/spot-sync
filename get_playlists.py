from os import mkdir
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from pathlib import Path
import shutil
import os.path
import re
import subprocess
import json

# Settings file path
SETTINGS_PATH = "settings.json"

def migrate_from_env():
    """Migrate settings from .env file to JSON if .env exists"""
    if os.path.exists('.env') and not os.path.exists(SETTINGS_PATH):
        try:
            # Simple parsing of .env file
            env_settings = {}
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        env_settings[key] = value
            
            # Convert to our settings format
            settings = {
                'CLIENT_ID': env_settings.get('CLIENT_ID', '') or env_settings.get('SPOTIPY_CLIENT_ID', ''),
                'CLIENT_SECRET': env_settings.get('CLIENT_SECRET', '') or env_settings.get('SPOTIPY_CLIENT_SECRET', ''),
                'USER': env_settings.get('USER', ''),
                'SYNC_FOLDER': env_settings.get('SYNC_FOLDER', os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync')),
                'YT_PREMIUM_ENABLED': env_settings.get('YT_PREMIUM_ENABLED', '').lower() == 'true',
                'YT_COOKIES_FILE': env_settings.get('YT_COOKIES_FILE', ''),
                'PLAYLIST_DELAY': 0,
                'RATE_LIMIT_WAIT': 0
            }
            
            # Save to JSON
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            print("Successfully migrated settings from .env to settings.json")
            return True
        except Exception as e:
            print(f"Migration failed: {e}")
    return False

def load_settings():
    """Load settings from JSON file"""
    # Try migration first
    migrate_from_env()
    
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default settings
        return {
            "CLIENT_ID": "",
            "CLIENT_SECRET": "",
            "USER": "",
            "SYNC_FOLDER": os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync'),
            "YT_PREMIUM_ENABLED": False,
            "YT_COOKIES_FILE": "",
            "PLAYLIST_DELAY": 0,
            "RATE_LIMIT_WAIT": 0
        }

# Load configuration from JSON
settings = load_settings()

# Configuration from settings
CLIENT_ID = settings.get('CLIENT_ID', '')
CLIENT_SECRET = settings.get('CLIENT_SECRET', '')
USER = settings.get('USER', '')
SYNC_FOLDER = settings.get('SYNC_FOLDER', os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync'))

# Create sync folder if it doesn't exist
os.makedirs(SYNC_FOLDER, exist_ok=True)

REMOVE = False

EXISTING_PLAYLISTS = os.listdir(SYNC_FOLDER) if os.path.exists(SYNC_FOLDER) else []

def authenticate():
    '''
    Authenticate Spotify api using Client Credentials Flow
    Note: This can only access public playlists, not private ones
    '''
    # Use module variables which are set by the GUI
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    
    # Validate credentials
    if not client_id:
        raise ValueError("No Client ID found. Please configure your settings.")
    if not client_secret:
        raise ValueError("No Client Secret found. Please configure your settings.")
    
    # Use Client Credentials Flow (no user authentication needed)
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp

def get_playlists(sp, user=USER):
    '''
    fetch playlists names from Spotify
    '''
    playlists = {}
    results = sp.user_playlists(user=user)
    for entry in results["items"]:
        playlist_name = re.sub(r"[^A-Za-z0-9]", "", entry["name"]) #remove whitespaces and stuff
        playlists[playlist_name] = entry["external_urls"]["spotify"]
    return playlists

def sync_single_playlist(url, name, use_yt_premium=False, cookies_file=''):
    '''
    Use spotdl to sync a single playlist 
    Supports YouTube Music Premium for higher quality downloads (256kbps)
    '''
    command = f"spotdl sync {url} --save-file {name}.sync.spotdl"
    
    # Add YouTube Music Premium options if enabled
    if use_yt_premium and cookies_file and os.path.exists(cookies_file):
        command += f" --cookie-file \"{cookies_file}\""
        # Always use M4A format with bitrate disabled for best quality
        command += " --format m4a"
        command += " --bitrate disable"
    
    print("run: ", command)
    
    # Use subprocess for better error handling
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            # Check if it's a rate limit error
            if "429" in result.stderr or "rate limit" in result.stderr.lower():
                raise Exception("Rate limit error: Too many requests to Spotify API")
            else:
                raise Exception(f"Command failed with error: {result.stderr}")
    except subprocess.SubprocessError as e:
        raise Exception(f"Failed to run spotdl: {str(e)}")

def sync_playlists(playlists, sync_folder=SYNC_FOLDER):
    '''
    create playlist classes for each playlist
    '''
    # Load current settings
    settings = load_settings()
    use_yt_premium = settings.get('YT_PREMIUM_ENABLED', False)
    cookies_file = settings.get('YT_COOKIES_FILE', '')
    
    for name, url in playlists.items():
        os.chdir(SYNC_FOLDER)
        Path(name).mkdir(parents=True, exist_ok=True)
        os.chdir(os.path.join(SYNC_FOLDER, name))
        sync_single_playlist(url, name, use_yt_premium, cookies_file)


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

