import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QTextEdit, QGroupBox, QMessageBox,
                               QListWidget, QProgressBar, QDialog, QDialogButtonBox,
                               QFormLayout, QToolButton, QTextBrowser, QCheckBox, 
                               QComboBox, QTabWidget, QListWidgetItem, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QTimer
from PySide6.QtGui import QIcon, QFont, QDesktopServices
import get_playlists
from pathlib import Path
from cookie_extractor import CookieExtractor
import time
import json

# Settings file path
SETTINGS_PATH = "settings.json"

def migrate_from_env():
    """Migrate settings from .env file to JSON if .env exists"""
    if os.path.exists('.env') and not os.path.exists(SETTINGS_PATH):
        try:
            from dotenv import dotenv_values
            env_settings = dotenv_values('.env')
            
            # Convert to our settings format
            settings = {
                'CLIENT_ID': env_settings.get('CLIENT_ID', '') or env_settings.get('SPOTIPY_CLIENT_ID', ''),
                'CLIENT_SECRET': env_settings.get('CLIENT_SECRET', '') or env_settings.get('SPOTIPY_CLIENT_SECRET', ''),
                'USER': env_settings.get('USER', ''),
                'SYNC_FOLDER': env_settings.get('SYNC_FOLDER', os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync')),
                'YT_PREMIUM_ENABLED': env_settings.get('YT_PREMIUM_ENABLED', '').lower() == 'true',
                'YT_COOKIES_FILE': env_settings.get('YT_COOKIES_FILE', ''),
                'PLAYLIST_DELAY': 0,  # No delays by default
                'RATE_LIMIT_WAIT': 0  # No wait by default
            }
            
            # Save to JSON
            save_settings(settings)
            print("Successfully migrated settings from .env to settings.json")
            return True
        except ImportError:
            # python-dotenv not installed, skip migration
            pass
    return False

def save_settings(settings: dict):
    """Save settings to JSON file"""
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def load_settings() -> dict:
    """Load settings from JSON file"""
    # Try migration first
    migrate_from_env()
    
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default settings on first run
        return {
            "CLIENT_ID": "",
            "CLIENT_SECRET": "",
            "USER": "",
            "SYNC_FOLDER": os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync'),
            "YT_PREMIUM_ENABLED": False,
            "YT_COOKIES_FILE": "",
            "PLAYLIST_DELAY": 0,  # Delay in seconds between playlists (0 = no delay)
            "RATE_LIMIT_WAIT": 0  # Wait time in seconds when rate limited (0 = no wait)
        }

class SettingsDialog(QDialog):
    """Settings dialog for configuration"""
    settings_saved = Signal()  # Signal emitted when settings are saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_if_ready)
        self._cached_browsers = None  # Cache available browsers
        self._loading_config = True  # Flag to prevent auto-save during initial load
        self.init_ui()
        self.load_config()
        self._loading_config = False  # Allow auto-save after initial load
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create tabs
        self.create_spotify_tab()
        self.create_user_tab()
        self.create_youtube_tab()
        self.create_about_tab()
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def create_spotify_tab(self):
        """Create Spotify API configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Help section
        help_group = QGroupBox("Getting Started")
        help_layout = QVBoxLayout()
        
        help_text = QTextBrowser()
        help_text.setMaximumHeight(200)
        help_text.setOpenExternalLinks(False)
        help_text.setHtml("""
        <style>
            body { font-family: Arial, sans-serif; font-size: 12px; }
            ol { margin: 5px 0; padding-left: 20px; }
            li { margin: 3px 0; }
            .important { color: #d32f2f; font-weight: bold; }
            .note { color: #ff9800; font-style: italic; }
        </style>
        <body>
        <p><b>To get your Spotify API credentials:</b></p>
        <ol>
            <li>Click the button below to open Spotify Developer Dashboard</li>
            <li>Log in with your Spotify account</li>
            <li>Click "Create app"</li>
            <li>Fill in:
                <ul>
                    <li>App name: <i>Spoti-Sync</i> (or any name)</li>
                    <li>App description: <i>Personal playlist sync tool</i></li>
                    <li>Website: <i>Leave empty</i></li>
                    <li>Redirect URI: <i>Not needed for this app</i></li>
                </ul>
            </li>
            <li>Check "Web API" under APIs used</li>
            <li>Click "Save"</li>
            <li>Copy your <b>Client ID</b> and <b>Client Secret</b> from the app settings</li>
        </ol>
        <p class="note">Note: This app uses Client Credentials authentication, which can only access public playlists.</p>
        </body>
        """)
        help_layout.addWidget(help_text)
        
        open_dashboard_btn = QPushButton("Open Spotify Developer Dashboard")
        open_dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)
        open_dashboard_btn.clicked.connect(self.open_spotify_dashboard)
        help_layout.addWidget(open_dashboard_btn)
        
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        # Spotify API Settings
        api_group = QGroupBox("API Credentials")
        api_layout = QFormLayout()
        
        # Client ID with show/hide toggle
        client_id_layout = QHBoxLayout()
        self.client_id_input = QLineEdit()
        self.client_id_input.setEchoMode(QLineEdit.Password)
        self.client_id_input.textChanged.connect(self.check_auto_save)
        client_id_layout.addWidget(self.client_id_input)
        self.toggle_client_id_btn = QPushButton("Show")
        self.toggle_client_id_btn.setMaximumWidth(50)
        self.toggle_client_id_btn.clicked.connect(lambda: self.toggle_visibility(self.client_id_input, self.toggle_client_id_btn))
        client_id_layout.addWidget(self.toggle_client_id_btn)
        api_layout.addRow("Client ID:", client_id_layout)
        
        # Client Secret with show/hide toggle
        client_secret_layout = QHBoxLayout()
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.Password)
        self.client_secret_input.textChanged.connect(self.check_auto_save)
        client_secret_layout.addWidget(self.client_secret_input)
        self.toggle_secret_btn = QPushButton("Show")
        self.toggle_secret_btn.setMaximumWidth(50)
        self.toggle_secret_btn.clicked.connect(lambda: self.toggle_visibility(self.client_secret_input, self.toggle_secret_btn))
        client_secret_layout.addWidget(self.toggle_secret_btn)
        api_layout.addRow("Client Secret:", client_secret_layout)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "Spotify API")
        
    def create_user_tab(self):
        """Create user configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # User Settings
        user_group = QGroupBox("User Configuration")
        user_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Your Spotify username")
        self.username_input.textChanged.connect(self.check_auto_save)
        user_layout.addRow("Spotify Username:", self.username_input)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Sync Settings
        sync_group = QGroupBox("Sync Configuration")
        sync_layout = QVBoxLayout()
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Sync Folder:"))
        self.folder_input = QLineEdit()
        folder_layout.addWidget(self.folder_input)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_button)
        sync_layout.addLayout(folder_layout)
        
        sync_info = QLabel("This is where your playlists will be downloaded")
        sync_info.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        sync_layout.addWidget(sync_info)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "User Settings")
        
    def create_youtube_tab(self):
        """Create YouTube Music Premium tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # YouTube Music Premium Settings
        yt_group = QGroupBox("YouTube Music Premium Settings")
        yt_layout = QVBoxLayout()
        
        # Enable YouTube Music Premium checkbox
        self.yt_premium_checkbox = QCheckBox("Enable YouTube Music Premium (256kbps)")
        self.yt_premium_checkbox.toggled.connect(self.toggle_yt_premium)
        yt_layout.addWidget(self.yt_premium_checkbox)
        
        # YouTube Music help text
        yt_help = QTextBrowser()
        yt_help.setMaximumHeight(120)
        yt_help.setHtml("""
        <style>
            body { font-family: Arial, sans-serif; font-size: 11px; }
            ol { margin: 2px 0; padding-left: 20px; }
            li { margin: 2px 0; }
            .note { color: #1976d2; }
            .important { color: #4CAF50; font-weight: bold; }
            .new { color: #FF5722; font-weight: bold; }
        </style>
        <body>
        <p><b>To use YouTube Music Premium:</b></p>
        <ol>
            <li>Log in to YouTube Music in your browser</li>
            <li>Set quality to highest in YouTube Music settings</li>
            <li class="new">Option A: Click your browser button below (may need browser closed)</li>
            <li class="new">Option B: Use "Get cookies.txt LOCALLY" extension and browse for file</li>
        </ol>
        <p class="note">Best quality settings are applied automatically:</p>
        <ul class="important">
            <li>M4A format (no re-encoding) • Bitrate disabled • 256kbps preserved</li>
        </ul>
        </body>
        """)
        yt_layout.addWidget(yt_help)
        
        # Browser extraction section
        browser_group = QGroupBox("Extract from Browser")
        browser_layout = QVBoxLayout()
        
        # Detect available browsers (cache the result)
        if self._cached_browsers is None:
            self._cached_browsers = CookieExtractor.get_available_browsers()
        
        if self._cached_browsers:
            browser_info = QLabel("Click on your browser to extract cookies automatically:")
            browser_info.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
            browser_layout.addWidget(browser_info)
            
            # Create buttons for each available browser
            browser_buttons_layout = QHBoxLayout()
            for browser_key, browser_name in self._cached_browsers:
                browser_btn = QPushButton(browser_name)
                browser_btn.setEnabled(False)
                browser_btn.clicked.connect(lambda checked, key=browser_key: self.extract_from_browser(key))
                browser_buttons_layout.addWidget(browser_btn)
                # Store reference for enabling/disabling
                setattr(self, f"browser_btn_{browser_key}", browser_btn)
            browser_layout.addLayout(browser_buttons_layout)
        else:
            no_browser_label = QLabel("No supported browsers detected")
            no_browser_label.setStyleSheet("color: #666; font-style: italic;")
            browser_layout.addWidget(no_browser_label)
        
        browser_group.setLayout(browser_layout)
        yt_layout.addWidget(browser_group)
        
        # Manual cookies file selection
        manual_group = QGroupBox("Manual Selection")
        manual_layout = QVBoxLayout()
        
        self.cookies_layout = QHBoxLayout()
        self.cookies_layout.addWidget(QLabel("Cookies File:"))
        self.cookies_input = QLineEdit()
        self.cookies_input.setEnabled(False)
        self.cookies_input.setPlaceholderText("No file selected")
        self.cookies_layout.addWidget(self.cookies_input)
        self.browse_cookies_button = QPushButton("Browse")
        self.browse_cookies_button.setEnabled(False)
        self.browse_cookies_button.clicked.connect(self.browse_cookies_file)
        self.cookies_layout.addWidget(self.browse_cookies_button)
        manual_layout.addLayout(self.cookies_layout)
        
        manual_group.setLayout(manual_layout)
        yt_layout.addWidget(manual_group)
        
        # Extension help button
        extension_btn = QPushButton("Get Browser Extension for Manual Export")
        extension_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        extension_btn.clicked.connect(self.open_extension_page)
        yt_layout.addWidget(extension_btn)
        
        yt_group.setLayout(yt_layout)
        layout.addWidget(yt_group)
        
        # Benefits info
        benefits_group = QGroupBox("Benefits")
        benefits_layout = QVBoxLayout()
        benefits_text = QLabel("""
        • 256kbps audio quality (vs 128kbps standard)
        • M4A format automatically selected
        • No bitrate limiting or re-encoding
        • Maximum audio fidelity preserved
        • Works with your existing YouTube Music subscription
        """)
        benefits_text.setStyleSheet("padding: 10px; color: #333;")
        benefits_layout.addWidget(benefits_text)
        benefits_group.setLayout(benefits_layout)
        layout.addWidget(benefits_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "YouTube Music")
        
    def create_about_tab(self):
        """Create about/info tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # About section
        about_group = QGroupBox("About Spoti-Sync")
        about_layout = QVBoxLayout()
        
        about_text = QTextBrowser()
        about_text.setOpenExternalLinks(True)
        about_text.setHtml("""
        <style>
            body { font-family: Arial, sans-serif; font-size: 13px; line-height: 1.6; }
            h2 { color: #1DB954; }
            a { color: #1976d2; }
        </style>
        <body>
        <h2>Spoti-Sync</h2>
        <p>A modern Spotify playlist synchronization tool with YouTube Music Premium support.</p>
        
        <p><b>Features:</b></p>
        <ul>
            <li>Download and sync public Spotify playlists</li>
            <li>Modern GUI interface</li>
            <li>YouTube Music Premium support (256kbps)</li>
            <li>Automatic playlist updates</li>
            <li>Multiple audio format support</li>
        </ul>
        
        <p><b>Built with:</b></p>
        <ul>
            <li>Python + PySide6 (Qt)</li>
            <li>Spotipy (Spotify Web API)</li>
            <li>spotDL (Download engine)</li>
        </ul>
        
        <p><b>Tips:</b></p>
        <ul>
            <li>Make sure your playlists are public to sync them</li>
            <li>Use M4A format with YouTube Music for best quality</li>
            <li>Check your sync folder regularly for updates</li>
        </ul>
        
        <p><b>Rate Limiting:</b></p>
        <p>By default, there are NO delays between downloads for maximum speed. If you encounter rate limits:</p>
        <ul>
            <li>The app will retry failed downloads immediately</li>
            <li>You can manually add delays by editing settings.json:</li>
            <li>&nbsp;&nbsp;- "PLAYLIST_DELAY": seconds between playlists (default: 0)</li>
            <li>&nbsp;&nbsp;- "RATE_LIMIT_WAIT": seconds to wait on 429 errors (default: 0)</li>
            <li>Most users won't need any delays</li>
        </ul>
        </body>
        """)
        
        about_layout.addWidget(about_text)
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "About")
        
    def check_auto_save(self):
        """Check if we should auto-save when both Client ID and Secret are entered"""
        # Don't auto-save during initial config loading
        if hasattr(self, '_loading_config') and self._loading_config:
            return
            
        # Stop any existing timer
        self.auto_save_timer.stop()
        
        # Check if both fields have values and username is set
        if (self.client_id_input.text() and 
            self.client_secret_input.text() and 
            self.username_input.text()):
            # Start timer to auto-save after 1.5 seconds of no typing
            self.auto_save_timer.start(1500)
    
    def auto_save_if_ready(self):
        """Auto-save settings if all required fields are filled"""
        if (self.client_id_input.text() and 
            self.client_secret_input.text() and 
            self.username_input.text()):
            # Save without showing the dialog
            self.save_settings_silently()
    
    def save_settings_silently(self):
        """Save settings without showing success dialog"""
        # Create settings dictionary
        settings = {
            'CLIENT_ID': self.client_id_input.text(),
            'CLIENT_SECRET': self.client_secret_input.text(),
            'USER': self.username_input.text(),
            'SYNC_FOLDER': self.folder_input.text(),
            'YT_PREMIUM_ENABLED': self.yt_premium_checkbox.isChecked(),
            'YT_COOKIES_FILE': self.cookies_input.text()
        }
        
        # Save to JSON file
        save_settings(settings)
        
        # Update get_playlists module variables
        get_playlists.CLIENT_ID = settings['CLIENT_ID']
        get_playlists.CLIENT_SECRET = settings['CLIENT_SECRET']
        get_playlists.USER = settings['USER']
        get_playlists.SYNC_FOLDER = settings['SYNC_FOLDER']
        
        # Create sync folder if it doesn't exist
        os.makedirs(settings['SYNC_FOLDER'], exist_ok=True)
        
        # Emit signal that settings were saved
        self.settings_saved.emit()
    
    def toggle_visibility(self, input_field, button):
        """Toggle password visibility"""
        if input_field.echoMode() == QLineEdit.Password:
            input_field.setEchoMode(QLineEdit.Normal)
            button.setText("Hide")
        else:
            input_field.setEchoMode(QLineEdit.Password)
            button.setText("Show")
            
    def open_spotify_dashboard(self):
        """Open Spotify Developer Dashboard in browser"""
        QDesktopServices.openUrl(QUrl("https://developer.spotify.com/dashboard"))
        
    def open_extension_page(self):
        """Open browser extension page for cookie export"""
        # Detect user's primary browser and open appropriate extension store
        if os.path.exists(os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe')):
            # Chrome Web Store
            QDesktopServices.openUrl(QUrl("https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"))
        elif os.path.exists(os.path.expandvars(r'%PROGRAMFILES%\Mozilla Firefox\firefox.exe')):
            # Firefox Add-ons
            QDesktopServices.openUrl(QUrl("https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/"))
        else:
            # Generic instructions
            QDesktopServices.openUrl(QUrl("https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"))
        
    def load_config(self):
        """Load configuration from JSON file"""
        settings = load_settings()
        
        # Load API credentials
        self.client_id_input.setText(settings.get('CLIENT_ID', ''))
        self.client_secret_input.setText(settings.get('CLIENT_SECRET', ''))
        self.username_input.setText(settings.get('USER', ''))
        
        # Load sync folder
        self.folder_input.setText(settings.get('SYNC_FOLDER', os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync')))
        
        # Load YouTube Music Premium settings
        self.yt_premium_checkbox.setChecked(settings.get('YT_PREMIUM_ENABLED', False))
        self.cookies_input.setText(settings.get('YT_COOKIES_FILE', ''))
        
    def browse_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Sync Folder",
            self.folder_input.text() or os.path.expanduser('~')
        )
        if folder:
            self.folder_input.setText(folder)
            
    def browse_cookies_file(self):
        """Open cookies file selection dialog"""
        file = QFileDialog.getOpenFileName(
            self,
            "Select Cookies File",
            "",
            "Cookies Files (*.txt)"
        )
        if file[0]:
            self.cookies_input.setText(file[0])
            
    def extract_from_browser(self, browser_key):
        """Extract cookies from selected browser"""
        browser_name = CookieExtractor.SUPPORTED_BROWSERS[browser_key]
        
        # Show initial message
        QMessageBox.information(self, "Extracting Cookies", 
                              f"Attempting to extract YouTube Music cookies from {browser_name}...\n\n"
                              "Note: This works best when the browser is closed.")
        
        # Extract cookies
        cookies_file, error = CookieExtractor.extract_youtube_cookies(browser_key)
        
        if cookies_file:
            # Verify the cookies contain YouTube login
            if CookieExtractor.verify_youtube_login(cookies_file):
                self.cookies_input.setText(cookies_file)
                QMessageBox.information(self, "Success", 
                                      f"Successfully extracted cookies from {browser_name}!\n\n"
                                      f"Cookies saved to:\n{cookies_file}")
            else:
                QMessageBox.warning(self, "No Login Found", 
                                  "Cookies were extracted but no YouTube Music login was found.\n\n"
                                  "Please log in to YouTube Music in your browser and try again.")
        else:
            # Check if it's an admin/permission error
            if "admin" in error.lower() or "permission" in error.lower() or "alternative" in error.lower():
                # Show detailed help dialog
                msg = QMessageBox(self)
                msg.setWindowTitle("Cookie Extraction Failed")
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"Cannot extract cookies from {browser_name}")
                msg.setDetailedText(error)
                
                # Add buttons for alternatives
                msg.setStandardButtons(QMessageBox.Ok)
                manual_btn = msg.addButton("Use Manual Method", QMessageBox.ActionRole)
                
                msg.exec()
                
                if msg.clickedButton() == manual_btn:
                    # Open instructions for manual method
                    QDesktopServices.openUrl(QUrl("https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"))
            else:
                QMessageBox.critical(self, "Extraction Failed", 
                                   f"Failed to extract cookies:\n{error}")
            
    def toggle_yt_premium(self, checked):
        """Toggle YouTube Music Premium settings"""
        self.cookies_input.setEnabled(checked)
        self.browse_cookies_button.setEnabled(checked)
        
        # Enable/disable browser buttons (use cached list)
        if self._cached_browsers:
            for browser_key, _ in self._cached_browsers:
                btn = getattr(self, f"browser_btn_{browser_key}", None)
                if btn:
                    btn.setEnabled(checked)
            
    def save_and_accept(self):
        """Save configuration and close dialog"""
        # Validate required fields
        if not self.client_id_input.text():
            QMessageBox.warning(self, "Missing Information", "Client ID is required")
            return
        if not self.client_secret_input.text():
            QMessageBox.warning(self, "Missing Information", "Client Secret is required")
            return
        if not self.username_input.text():
            QMessageBox.warning(self, "Missing Information", "Spotify Username is required")
            return
            
        # Create settings dictionary
        settings = {
            'CLIENT_ID': self.client_id_input.text(),
            'CLIENT_SECRET': self.client_secret_input.text(),
            'USER': self.username_input.text(),
            'SYNC_FOLDER': self.folder_input.text(),
            'YT_PREMIUM_ENABLED': self.yt_premium_checkbox.isChecked(),
            'YT_COOKIES_FILE': self.cookies_input.text()
        }
        
        # Save to JSON file
        save_settings(settings)
        
        # Update get_playlists module variables
        get_playlists.CLIENT_ID = settings['CLIENT_ID']
        get_playlists.CLIENT_SECRET = settings['CLIENT_SECRET']
        get_playlists.USER = settings['USER']
        get_playlists.SYNC_FOLDER = settings['SYNC_FOLDER']
        
        # Create sync folder if it doesn't exist
        os.makedirs(settings['SYNC_FOLDER'], exist_ok=True)
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
        self.settings_saved.emit()  # Emit signal when settings are saved
        self.accept()

class SyncWorker(QThread):
    """Worker thread for running sync operations"""
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()
    status_signal = Signal(str)  # For updating status label
    
    def __init__(self, playlists):
        super().__init__()
        self.playlists = playlists
        
    def run(self):
        try:
            self.log_signal.emit("Starting sync...")
            total = len(self.playlists)
            
            # Load settings for YouTube Music Premium and delays
            settings = load_settings()
            use_yt_premium = settings.get('YT_PREMIUM_ENABLED', False)
            cookies_file = settings.get('YT_COOKIES_FILE', '')
            playlist_delay = settings.get('PLAYLIST_DELAY', 0)
            rate_limit_wait = settings.get('RATE_LIMIT_WAIT', 0)
            
            for i, (name, url) in enumerate(self.playlists.items()):
                try:
                    self.log_signal.emit(f"Syncing playlist: {name}")
                    
                    # Create playlist folder
                    playlist_folder = os.path.join(get_playlists.SYNC_FOLDER, name)
                    Path(playlist_folder).mkdir(parents=True, exist_ok=True)
                    
                    # Change to playlist directory and sync
                    original_dir = os.getcwd()
                    os.chdir(playlist_folder)
                    
                    if use_yt_premium and cookies_file and os.path.exists(cookies_file):
                        self.log_signal.emit(f"  Using YouTube Music Premium (M4A @ 256kbps)")
                    
                    get_playlists.sync_single_playlist(url, name, use_yt_premium, cookies_file)
                    os.chdir(original_dir)
                    
                    # Update progress
                    progress = int(((i + 1) / total) * 100)
                    self.progress_signal.emit(progress)
                    
                    # Optional delay between playlists
                    if playlist_delay > 0 and i < total - 1:
                        self.log_signal.emit(f"  Waiting {playlist_delay} seconds before next playlist...")
                        self.status_signal.emit(f"Waiting {playlist_delay}s to avoid rate limits...")
                        time.sleep(playlist_delay)
                        self.status_signal.emit(f"Syncing playlists... ({i+1}/{total})")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "rate limit" in error_msg.lower():
                        if rate_limit_wait > 0:
                            self.log_signal.emit(f"  ⚠️ Rate limit hit for {name}. Waiting {rate_limit_wait} seconds...")
                            time.sleep(rate_limit_wait)
                        else:
                            self.log_signal.emit(f"  ⚠️ Rate limit hit for {name}. Retrying immediately...")
                        # Try once more
                        try:
                            self.log_signal.emit(f"  Retrying {name}...")
                            os.chdir(playlist_folder)
                            get_playlists.sync_single_playlist(url, name, use_yt_premium, cookies_file)
                            os.chdir(original_dir)
                            progress = int(((i + 1) / total) * 100)
                            self.progress_signal.emit(progress)
                        except Exception as retry_error:
                            self.log_signal.emit(f"  ❌ Failed to sync {name}: {str(retry_error)}")
                    else:
                        self.log_signal.emit(f"  ❌ Error syncing {name}: {error_msg}")
                
            self.log_signal.emit("✅ Sync completed!")
        except Exception as e:
            self.log_signal.emit(f"❌ Critical error: {str(e)}")
        finally:
            self.finished_signal.emit()

class SpotiSyncGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sp = None
        self.playlists = {}
        self.auto_authenticated = False  # Track if we've auto-authenticated
        self.init_ui()
        self.check_configuration()
        
    def init_ui(self):
        self.setWindowTitle("Spoti-Sync")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header with title and settings button
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Spoti-Sync")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Settings button (cogwheel)
        self.settings_button = QToolButton()
        self.settings_button.setText("⚙")  # Cogwheel unicode character
        self.settings_button.setToolTip("Settings")
        self.settings_button.setStyleSheet("""
            QToolButton {
                font-size: 24px;
                border: none;
                padding: 5px;
                border-radius: 5px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.settings_button.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_button)
        
        main_layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel("Not authenticated")
        self.status_label.setStyleSheet("color: #666; padding: 10px;")
        main_layout.addWidget(self.status_label)
        
        # Playlists group
        playlists_group = QGroupBox("Your Playlists")
        playlists_layout = QVBoxLayout()
        
        # Create scroll area for playlist checkboxes
        self.playlists_scroll = QScrollArea()
        self.playlists_scroll.setWidgetResizable(True)
        self.playlists_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
        """)
        
        # Container widget for checkboxes
        self.playlists_container = QWidget()
        self.playlists_container_layout = QVBoxLayout(self.playlists_container)
        self.playlists_container_layout.setAlignment(Qt.AlignTop)
        self.playlists_container_layout.setSpacing(2)
        self.playlists_container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.playlists_scroll.setWidget(self.playlists_container)
        playlists_layout.addWidget(self.playlists_scroll)
        
        # Store checkbox references
        self.playlist_checkboxes = {}
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_playlists)
        self.select_all_button.setEnabled(False)
        selection_layout.addWidget(self.select_all_button)
        
        self.deselect_all_button = QPushButton("Deselect All")
        self.deselect_all_button.clicked.connect(self.deselect_all_playlists)
        self.deselect_all_button.setEnabled(False)
        selection_layout.addWidget(self.deselect_all_button)
        
        playlists_layout.addLayout(selection_layout)
        
        self.refresh_button = QPushButton("Refresh Playlists")
        self.refresh_button.clicked.connect(self.refresh_playlists)
        self.refresh_button.setEnabled(False)
        playlists_layout.addWidget(self.refresh_button)
        
        playlists_group.setLayout(playlists_layout)
        main_layout.addWidget(playlists_group)
        
        # Sync button and progress
        self.sync_button = QPushButton("Start Sync")
        self.sync_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5CBF60;
            }
            QPushButton:pressed {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.sync_button.clicked.connect(self.start_sync)
        self.sync_button.setEnabled(False)
        main_layout.addWidget(self.sync_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                font-family: monospace;
                background-color: #f5f5f5;
                color: #212121;
            }
        """)
        main_layout.addWidget(self.log_output)
        
    def check_configuration(self):
        """Check if configuration is complete and auto-authenticate if possible"""
        settings = load_settings()
        client_id = settings.get('CLIENT_ID', '')
        client_secret = settings.get('CLIENT_SECRET', '')
        user = settings.get('USER', '')
        
        if all([client_id, client_secret, user]):
            self.status_label.setText("Credentials found, connecting...")
            self.status_label.setStyleSheet("color: #FF9800; padding: 10px;")
            # Auto-authenticate if we haven't already
            if not self.auto_authenticated and not self.sp:
                self.auto_authenticated = True
                # Use a timer to authenticate after the window is shown
                QTimer.singleShot(500, self.authenticate)
        else:
            self.status_label.setText("Please configure settings first (click ⚙)")
            self.status_label.setStyleSheet("color: #f44336; padding: 10px;")
            
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_saved.connect(self.on_settings_saved)
        if dialog.exec():
            self.check_configuration()
            
    def on_settings_saved(self):
        """Called when settings are saved in the dialog"""
        # Reset auto-authentication flag so it can try again with new credentials
        self.auto_authenticated = False
        self.check_configuration()
            
    def authenticate(self):
        """Authenticate with Spotify"""
        try:
            settings = load_settings()
            client_id = settings.get('CLIENT_ID', '')
            client_secret = settings.get('CLIENT_SECRET', '')
            user = settings.get('USER', '')
            
            if not all([client_id, client_secret, user]):
                QMessageBox.warning(self, "Missing Configuration", 
                                  "Please configure your settings first (click the ⚙ button).")
                return
                
            # Update get_playlists module variables
            get_playlists.CLIENT_ID = client_id
            get_playlists.CLIENT_SECRET = client_secret
            get_playlists.USER = user
            get_playlists.SYNC_FOLDER = settings.get('SYNC_FOLDER', os.path.join(os.path.expanduser('~'), 'Music', 'Spoti-Sync'))
                
            self.log_output.append("Connecting to Spotify API...")
            self.sp = get_playlists.authenticate()
            self.log_output.append("Successfully connected to Spotify API!")
            self.log_output.append("Note: Only public playlists can be accessed with Client Credentials authentication.")
            
            self.status_label.setText(f"Connected - Viewing playlists for: {user}")
            self.status_label.setStyleSheet("color: #4CAF50; padding: 10px;")
            
            self.refresh_button.setEnabled(True)
            self.refresh_playlists()
            
        except Exception as e:
            self.log_output.append(f"Authentication failed: {str(e)}")
            self.status_label.setText("Authentication failed")
            self.status_label.setStyleSheet("color: #f44336; padding: 10px;")
            # Don't show error dialog on auto-authentication
            if hasattr(self, '_manual_auth'):
                QMessageBox.critical(self, "Authentication Error", 
                                   f"Failed to authenticate: {str(e)}")
            
    def refresh_playlists(self):
        """Fetch playlists from Spotify"""
        try:
            self.log_output.append("Fetching playlists...")
            settings = load_settings()
            user = settings.get('USER', '')
            self.playlists = get_playlists.get_playlists(self.sp, user)
            
            # Clear existing checkboxes
            while self.playlists_container_layout.count():
                child = self.playlists_container_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Clear checkbox references
            self.playlist_checkboxes.clear()
            
            # Create new checkboxes
            for name in self.playlists.keys():
                checkbox = QCheckBox(name)
                checkbox.setChecked(True)  # Default to checked
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 8px;
                        font-size: 14px;
                        border-bottom: 1px solid #eee;
                    }
                    QCheckBox:hover {
                        background-color: #f5f5f5;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                    }
                    QCheckBox::indicator:unchecked {
                        border: 2px solid #999;
                        border-radius: 3px;
                        background-color: white;
                    }
                    QCheckBox::indicator:unchecked:hover {
                        border: 2px solid #1DB954;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #1DB954;
                        border: 2px solid #1DB954;
                        border-radius: 3px;
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #1ed760;
                        border: 2px solid #1ed760;
                    }
                """)
                checkbox.stateChanged.connect(self.update_sync_button_text)
                self.playlist_checkboxes[name] = checkbox
                self.playlists_container_layout.addWidget(checkbox)
                
            self.log_output.append(f"Found {len(self.playlists)} playlists")
            self.sync_button.setEnabled(True)
            self.select_all_button.setEnabled(True)
            self.deselect_all_button.setEnabled(True)
            self.update_sync_button_text()
            
        except Exception as e:
            self.log_output.append(f"Failed to fetch playlists: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to fetch playlists: {str(e)}")
            
    def start_sync(self):
        """Start the sync process"""
        if not self.playlists:
            QMessageBox.warning(self, "No Playlists", 
                              "Please authenticate and fetch playlists first.")
            return
        
        # Get only checked playlists
        checked_playlists = {}
        for name, checkbox in self.playlist_checkboxes.items():
            if checkbox.isChecked():
                checked_playlists[name] = self.playlists[name]
        
        if not checked_playlists:
            QMessageBox.warning(self, "No Playlists Selected", 
                              "Please select at least one playlist to sync.")
            return
            
        # Disable buttons during sync
        self.sync_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.deselect_all_button.setEnabled(False)
        
        # Log selected playlists
        self.log_output.append(f"Syncing {len(checked_playlists)} selected playlist(s)...")
        
        # Create and start worker thread with only checked playlists
        self.sync_worker = SyncWorker(checked_playlists)
        self.sync_worker.log_signal.connect(self.log_output.append)
        self.sync_worker.progress_signal.connect(self.progress_bar.setValue)
        self.sync_worker.status_signal.connect(lambda msg: self.status_label.setText(msg))
        self.sync_worker.finished_signal.connect(self.sync_finished)
        self.sync_worker.start()
        
    def sync_finished(self):
        """Handle sync completion"""
        self.sync_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.select_all_button.setEnabled(True)
        self.deselect_all_button.setEnabled(True)
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "Sync Complete", "Playlist sync completed!")

    def select_all_playlists(self):
        """Select all playlists in the list"""
        for name, checkbox in self.playlist_checkboxes.items():
            checkbox.setChecked(True)
        self.update_sync_button_text()
    
    def deselect_all_playlists(self):
        """Deselect all playlists in the list"""
        for name, checkbox in self.playlist_checkboxes.items():
            checkbox.setChecked(False)
        self.update_sync_button_text()

    def update_sync_button_text(self):
        """Update sync button text to show the number of selected playlists"""
        checked_count = sum(checkbox.isChecked() for checkbox in self.playlist_checkboxes.values())
        
        if checked_count == 0:
            self.sync_button.setText("Start Sync")
        else:
            self.sync_button.setText(f"Start Sync ({checked_count} selected)")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    window = SpotiSyncGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
    