import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
SYNC_FOLDER = os.getenv('SYNC_FOLDER', './playlists')

def initialize_folder():
    pass
    # check if folder is empty 
    # if not ask if it should be created
    # if yes: create it

def ask_for_initials():
    pass

def ask_for_folder():
    pass

def check_if_folder_is_empty():
    pass

def create_folder_if_not_exist():
    pass

def setup_autostart():
    pass


def run():
    pass
    # ask_for_initials
    # ask_for_folders
    # check_if_folder_is_empty
    # create_folder_if_not_exist
    # setup_autostart and run loop