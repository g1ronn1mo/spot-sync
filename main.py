from get_playlists import *

if __name__ == "__main__":
    print("Starting spotisync")
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

