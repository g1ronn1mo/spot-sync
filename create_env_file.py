#!/usr/bin/env python3
"""
Helper script to create a .env file for Spotify Sync configuration
"""

def create_env_file():
    print("Creating .env file for Spotify Sync configuration...")
    print("\nYou'll need to provide your Spotify API credentials.")
    print("You can get these from https://developer.spotify.com/dashboard/applications\n")
    
    # Get configuration values
    client_id = input("Enter your Spotify CLIENT_ID: ").strip()
    client_secret = input("Enter your Spotify CLIENT_SECRET: ").strip()
    redirect_uri = input("Enter your REDIRECT_URI (press Enter for default http://localhost:8888/callback): ").strip()
    if not redirect_uri:
        redirect_uri = "http://localhost:8888/callback"
    
    username = input("Enter your Spotify username: ").strip()
    sync_folder = input("Enter sync folder path (press Enter for default ./playlists): ").strip()
    if not sync_folder:
        sync_folder = "./playlists"
    
    # Write to .env file
    env_content = f"""# Spotify API Configuration
CLIENT_ID={client_id}
CLIENT_SECRET={client_secret}
REDIRECT_URI={redirect_uri}

# User Configuration
USER={username}

# Sync Configuration
SYNC_FOLDER={sync_folder}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully!")
    print("You can now run: uv run python main.py")

if __name__ == "__main__":
    create_env_file() 