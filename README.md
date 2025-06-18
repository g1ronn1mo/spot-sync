# Spoti-Sync

A modern Spotify playlist synchronization tool with YouTube Music Premium support.

## Features

- Download and sync public Spotify playlists
- Modern GUI interface with PySide6 (Qt)
- YouTube Music Premium support (256kbps)
- Automatic playlist updates
- Multiple audio format support
- Selective playlist syncing with checkboxes
- Rate limit protection with automatic retries
- Persistent settings stored in JSON format

## Requirements

- Python 3.8+
- Spotify Developer Account (free)
- YouTube Music Premium subscription (optional, for 256kbps quality)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/spoti-sync.git
cd spoti-sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python gui.py
```

## Setup

### 1. Spotify API Credentials

1. Open the application and click the settings button (⚙)
2. Click "Open Spotify Developer Dashboard"
3. Create a new app:
   - App name: `Spoti-Sync` (or any name)
   - App description: `Personal playlist sync tool`
   - Check "Web API" under APIs used
4. Copy your Client ID and Client Secret
5. Enter them in the settings dialog

### 2. YouTube Music Premium (Optional)

For 256kbps audio quality:

1. Enable "YouTube Music Premium" in settings
2. Either:
   - Click your browser button to auto-extract cookies
   - Or use "Get cookies.txt LOCALLY" extension and browse for the file

## Usage

1. **Configure**: Enter your Spotify credentials and username in settings
2. **Authenticate**: The app will automatically connect when credentials are provided
3. **Select Playlists**: Use checkboxes to select which playlists to sync
   - Use "Select All" / "Deselect All" buttons for convenience
4. **Sync**: Click "Start Sync" to download selected playlists

## Features in Detail

### Selective Playlist Syncing
- Each playlist has a checkbox for selection
- Only checked playlists will be synced
- "Select All" and "Deselect All" buttons for batch operations

### Rate Limit Protection
- Downloads run at maximum speed with no artificial delays
- Automatic retry on rate limit errors
- Configurable delays if needed (edit settings.json):
  - `PLAYLIST_DELAY`: seconds between playlists (default: 0)
  - `RATE_LIMIT_WAIT`: seconds to wait on 429 errors (default: 0)
- Per-playlist error handling

### YouTube Music Premium
- Automatic M4A format selection
- Bitrate disabled to preserve original 256kbps quality
- Cookie-based authentication for premium access

### Settings Storage
- All settings are stored in `settings.json`
- Settings persist between application sessions
- Automatic migration from older `.env` format if found

## Notes

- Only public Spotify playlists can be accessed with Client Credentials authentication
- Playlists are downloaded to `~/Music/Spoti-Sync` by default
- The sync folder can be changed in settings
- Settings are saved in `settings.json` in the application directory

## Troubleshooting

### Authentication Issues
- Ensure Client ID and Secret are correct
- Check that your Spotify username is entered correctly

### YouTube Music Premium
- Make sure you're logged into YouTube Music in your browser
- Close your browser before attempting cookie extraction
- Use manual cookie export if automatic extraction fails

### Rate Limiting
- The app handles rate limits automatically
- For large collections, consider syncing in smaller batches

## License

This project is for personal use only. Please respect copyright laws and terms of service.
