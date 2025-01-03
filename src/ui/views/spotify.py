# spotify.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Button, Static, Input
from textual import work
import asyncio
from ...core.database.tick_db import CalendarDB
from textual.binding import Binding
from textual.message import Message
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import webbrowser
from dotenv import load_dotenv
import os
import threading
from .spotify_auth import start_auth_server, SpotifyCallbackHandler

load_dotenv()

class SpotifyAuth:
    def __init__(self, db: CalendarDB):
        self.db = db
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        
        self.scope = " ".join([
            "user-library-read",
            "playlist-read-private",
            "user-read-private",
            "user-read-email",
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-read-currently-playing",
            "streaming",
            "app-remote-control",
            "user-read-recently-played",
            "user-top-read",
            "playlist-read-collaborative"
        ])
        
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        
        self.spotify_client = None
        self._try_restore_session()
    
    def _try_restore_session(self) -> bool:
        """Try to restore a previous session from stored tokens."""
        stored_tokens = self.db.get_spotify_tokens()
        if not stored_tokens:
            return False
            
        # check if current token is still valid
        expiry = datetime.fromisoformat(stored_tokens['token_expiry'])
        if expiry > datetime.now():
            self.spotify_client = spotipy.Spotify(auth=stored_tokens['access_token'])
            return True
            
        # token expired, try to refresh
        try:
            token_info = self.sp_oauth.refresh_access_token(stored_tokens['refresh_token'])
            if token_info:
                self.spotify_client = spotipy.Spotify(auth=token_info['access_token'])
                self.db.save_spotify_tokens(
                    token_info['access_token'],
                    token_info['refresh_token'],
                    datetime.now() + timedelta(seconds=token_info['expires_in'])
                )
                return True
        except:
            return False
        
        return False

    def start_auth(self) -> bool:
        auth_url = self.sp_oauth.get_authorize_url()
        
        server_thread = threading.Thread(target=start_auth_server)
        server_thread.daemon = True
        server_thread.start()
        
        webbrowser.open(auth_url)
        
        server_thread.join()
        
        if SpotifyCallbackHandler.auth_code:
            try:
                token_info = self.sp_oauth.get_access_token(SpotifyCallbackHandler.auth_code)
                if token_info:
                    self.spotify_client = spotipy.Spotify(auth=token_info['access_token'])
                    self.db.save_spotify_tokens(
                        token_info['access_token'],
                        token_info['refresh_token'],
                        datetime.now() + timedelta(seconds=token_info['expires_in'])
                    )
                    return True
            except Exception as e:
                print(f"Authentication error: {e}")
                return False
        return False

class SearchResult(Static):
    class Selected(Message):
        def __init__(self, result_id: str, result_type: str) -> None:
            self.result_id = result_id
            self.result_type = result_type
            super().__init__()

    def __init__(self, title: str, result_id: str, result_type: str, artist: str = "") -> None:
        super().__init__()
        self.title = title
        self.result_id = result_id
        self.result_type = result_type
        self.artist = artist

    def compose(self) -> ComposeResult:
        self.classes = "spotify-track-button"
        yield Static(f"{'🎵' if self.result_type == 'track' else '📁'} {self.title}")
        if self.artist:
            yield Static(f"  by {self.artist}", classes="result-artist")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.result_id, self.result_type))

class SpotifyPlayer(Container):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Play/Pause", id="play-pause"),
            Button("Previous", id="prev-track"),
            Button("Next", id="next-track"),
        )

    def on_button_pressed(self, event: Button.Pressed):
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            self.notify("No Spotify client available", severity="error")
            return

        try:
            current_playback = spotify_client.current_playback()
            
            # print(f"Current playback state: {current_playback}")
            
            if not current_playback:
                self.notify("No active playback found. Start playing something first.", severity="error")
                return
            
            # set our context
            context = current_playback.get('context')
            print(f"Current context: {context}")
            
            if event.button.id == "play-pause":
                event.stop()
                try:
                    if current_playback["is_playing"]:
                        spotify_client.pause_playback()
                    else:
                        spotify_client.start_playback()
                except Exception as e:
                    print(f"Playback error: {str(e)}")
                    self.notify("Error controlling playback", severity="error")
            
            elif event.button.id == "next-track":
                event.stop()
                try:
                    # we check if we have a valid context of the playlist
                    if not context:
                        self.notify("No playlist context found. Try selecting a track from a playlist.", severity="warning")
                        return
                    spotify_client.next_track()
                except Exception as e:
                    print(f"Next track error: {str(e)}")
                    self.notify("Error skipping to next track", severity="error")
            
            elif event.button.id == "prev-track":
                event.stop()
                try:
                    # same thing here
                    if not context:
                        self.notify("No playlist context found. Try selecting a track from a playlist.", severity="warning")
                        return
                    spotify_client.previous_track()
                except Exception as e:
                    print(f"Previous track error: {str(e)}")
                    self.notify("Error going to previous track", severity="error")
                
        except Exception as e:
            print(f"Player error: {str(e)}")
            self.notify("Error controlling playback", severity="error")
            
class PlaylistItem(Static):
    class Selected(Message):
        def __init__(self, playlist_id: str) -> None:
            self.playlist_id = playlist_id
            super().__init__()

    def __init__(self, playlist_name: str, playlist_id: str) -> None:
        super().__init__()
        self.playlist_name = playlist_name
        self.playlist_id = playlist_id

    def compose(self) -> ComposeResult:
        self.classes = "spotify-playlist-item"
        yield Static(f"📁 {self.playlist_name}", classes="playlist-name")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.playlist_id))

class SearchBar(Container):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("🔍", classes="search-icon"),
            Input(placeholder="Search tracks and playlists...", classes="search-input"),
            classes="search-container"
        )

class SearchResult(Static):
    """
    A widget representing a search result (track or playlist) in the Spotify interface.
    """
    
    class Selected(Message):
        """Message emitted when a search result is selected."""
        def __init__(self, result_id: str, result_type: str, position: int = None) -> None:
            self.result_id = result_id
            self.result_type = result_type
            self.position = position
            super().__init__()

    def __init__(
        self, 
        title: str, 
        result_id: str, 
        result_type: str, 
        artist: str = "", 
        position: int = None
    ) -> None:
        """Initialize a new search result widget.
        
        Args:
            title: The title of the track or playlist
            result_id: The Spotify ID of the track or playlist
            result_type: Either 'track' or 'playlist'
            artist: The artist name (for tracks only)
            position: The position of this track in its playlist (optional)
        """
        super().__init__()
        self.title = title
        self.result_id = result_id
        self.result_type = result_type
        self.artist = artist
        self.position = position

    def compose(self) -> ComposeResult:
        """Compose the widget's view."""
        self.classes = "spotify-track-button"
        yield Static(f"{'🎵' if self.result_type == 'track' else '📁'} {self.title}")
        if self.artist:
            yield Static(f"  by {self.artist}", classes="result-artist")

    def on_click(self) -> None:
        """Handle click events by posting a Selected message."""
        self.post_message(self.Selected(
            self.result_id, 
            self.result_type,
            self.position
        ))

class LibrarySection(Container):
    def compose(self) -> ComposeResult:
        yield Button("Authenticate Spotify", id="auth-btn", variant="primary", classes="connect-spotify-button")
        yield ScrollableContainer(
            id="playlists-container",
            classes="playlists-scroll"
        )

    # debug log to test pulling of user playlists
    def load_playlists(self, spotify_client):
        with open("spotify_debug.log", "a") as f:
            f.write("\n--- Starting playlist load ---\n")
            if spotify_client:
                try:
                    # Try to ensure client is valid first
                    f.write("Testing connection...\n")
                    spotify_client.current_user()
                    
                    f.write("Fetching playlists...\n")
                    playlists = spotify_client.current_user_playlists()
                    f.write(f"Found {len(playlists['items'])} playlists\n")
                    
                    container = self.query_one("#playlists-container")
                    f.write("Found container, clearing children...\n")
                    container.remove_children()
                    
                    container.mount(Static("Your Library", classes="section-header"))
                    container.mount(Static("Playlists", classes="subsection-header"))
                    
                    container.mount(PlaylistItem("Liked Songs", "liked_songs"))
                    
                    for playlist in playlists['items']:
                        name = playlist['name'] if playlist['name'] else "Untitled Playlist"
                        container.mount(PlaylistItem(name, playlist['id']))
                        f.write(f"Added playlist: {name}\n")
                    
                    f.write("Finished loading playlists successfully\n")
                    return True
                    
                except spotipy.exceptions.SpotifyException as e:
                    error_msg = f"Spotify API error: {str(e)}\n"
                    f.write(error_msg)
                    container = self.query_one("#playlists-container")
                    container.mount(Static("⚠️ " + error_msg, classes="error-message"))
                    return False
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}\n"
                    f.write(error_msg)
                    container = self.query_one("#playlists-container")
                    container.mount(Static("⚠️ " + error_msg, classes="error-message"))
                    return False
            else:
                f.write("No Spotify client available!\n")
                return False

class PlaylistView(Container):
    def __init__(self) -> None:
        super().__init__()
        self.current_playlist_id = None

    def compose(self) -> ComposeResult:
        """Create the playlist view components."""
        yield Static("Select a playlist", id="playlist-title", classes="content-header")
        yield ScrollableContainer(
            id="tracks-container",
            classes="tracks-scroll"
        )

    def load_playlist(self, spotify_client, playlist_id: str) -> None:
        if not spotify_client:
            return

        try:
            self.current_playlist_id = playlist_id
            tracks_container = self.query_one("#tracks-container")
            if tracks_container:
                tracks_container.remove_children()

            if playlist_id == "liked_songs":
                results = spotify_client.current_user_saved_tracks()
                self.query_one("#playlist-title").update("Liked Songs")
                for i, item in enumerate(results['items']):
                    track_info = item['track']
                    tracks_container.mount(SearchResult(
                        track_info['name'],
                        track_info['id'],
                        'track',
                        ", ".join(artist['name'] for artist in track_info['artists']),
                        position=i
                    ))
            else:
                playlist = spotify_client.playlist(playlist_id)
                self.query_one("#playlist-title").update(playlist['name'])
                for i, item in enumerate(playlist['tracks']['items']):
                    track_info = item['track']
                    if track_info:
                        tracks_container.mount(SearchResult(
                            track_info['name'],
                            track_info['id'],
                            'track',
                            ", ".join(artist['name'] for artist in track_info['artists']),
                            position=i
                        ))
        except Exception as e:
            print(f"Error loading playlist: {e}")
            self.query_one("#playlist-title").update("Error loading playlist")

class MainContent(Container):
    def compose(self) -> ComposeResult:
        yield PlaylistView()

class SpotifyView(Container):
    BINDINGS = [
        Binding("ctrl+l", "focus_search", "Search"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.auth = SpotifyAuth(self.app.db)

    # If we restored a session, update the UI
        if self.auth.spotify_client:
            self.app.set_spotify_auth(self.auth)
            # We'll need to call this after mount
            self.call_after_refresh = True
        else:
            self.call_after_refresh = False
    
    def on_mount(self) -> None:
        if self.call_after_refresh:
            library_section = self.query_one(LibrarySection)
            library_section.load_playlists(self.auth.spotify_client)
    
    def compose(self) -> ComposeResult:
        # Dock the player at the top
        yield SpotifyPlayer()
        yield Container(
            Static("Spotify", id="status-bar-title", classes="status-item"),
            Static("Connected 🟢", id="status-bar-connection", classes="status-item-right"),
            classes="status-bar"
        )
        yield Container(
            Container(
                Container(
                    Static("Playlists", classes="section-title"),
                    LibrarySection(),
                    classes="playlists-section"
                ),
                Container(
                    Static("Instructions", classes="section-title"),
                    Static("⌘+L: Search", classes="instruction-item"),
                    Static("⌘+R: Refresh", classes="instruction-item"),
                    Static("Space: Play/Pause", classes="instruction-item"),
                    classes="instructions-section"
                ),
                classes="sidebar"
            ),
            Container(
                MainContent(),
                classes="main-content"
            ),
            classes="spotify-container"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-btn":
            self.notify("Starting Spotify authentication...")
            self.action_authenticate()
            self.app.set_spotify_auth(self.auth)  
            event.stop()


    @work
    async def do_auth(self):
        self.auth.start_auth()
        while not SpotifyCallbackHandler.auth_code:
            await asyncio.sleep(1)
        try:
            token_info = self.auth.sp_oauth.get_access_token(SpotifyCallbackHandler.auth_code)
            if token_info:
                self.auth.spotify_client = spotipy.Spotify(auth=token_info["access_token"])
                library_section = self.query_one(LibrarySection)
                library_section.load_playlists(self.auth.spotify_client)
                self.notify("Successfully connected to Spotify!")
            else:
                self.notify("Failed to authenticate with Spotify", severity="error")
        except:
            self.notify("Failed to authenticate with Spotify", severity="error")

    def action_authenticate(self):
        self.do_auth()

    def get_spotify_client(self):
        return self.auth.spotify_client

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self.auth.spotify_client:
            return

        query = event.value.strip()
        if not query:
            self.query_one(SearchResults).query_one("#results-container").remove_children()
            return

        try:
            results = self.auth.spotify_client.search(q=query, type='track,playlist', limit=5)
            
            results_container = self.query_one(SearchResults).query_one("#results-container")
            results_container.remove_children()

            if results['tracks']['items']:
                results_container.mount(Static("Songs", classes="results-section-header"))
                for track in results['tracks']['items']:
                    results_container.mount(SearchResult(
                        track['name'],
                        track['id'],
                        'track',
                        ", ".join(artist['name'] for artist in track['artists'])
                    ))

            if results['playlists']['items']:
                results_container.mount(Static("Playlists", classes="results-section-header"))
                for playlist in results['playlists']['items']:
                    results_container.mount(SearchResult(
                        playlist['name'],
                        playlist['id'],
                        'playlist'
                    ))
        except Exception as e:
            print(f"Search error: {e}")
            self.notify("Search failed", severity="error")

    def on_playlist_item_selected(self, message: PlaylistItem.Selected) -> None:
        playlist_view = self.query_one(PlaylistView)
        playlist_view.load_playlist(self.auth.spotify_client, message.playlist_id)

    def on_search_result_selected(self, message: SearchResult.Selected) -> None:
        if message.result_type == 'playlist':
            playlist_view = self.query_one(PlaylistView)
            playlist_view.load_playlist(self.auth.spotify_client, message.result_id)
        elif message.result_type == 'track':
            try:
                devices = self.auth.spotify_client.devices()
                if not devices['devices']:
                    self.notify("No Spotify devices found. Please open Spotify on any device.", severity="error")
                    return
                        
                active_device = next((d for d in devices['devices'] if d['is_active']), devices['devices'][0])
                
                # Get the current playlist context if we're in one
                playlist_view = self.query_one(PlaylistView)
                current_playlist_id = playlist_view.current_playlist_id
                
                if current_playlist_id and current_playlist_id != "liked_songs":
                    # If we have a position, use it directly
                    if message.position is not None:
                        self.auth.spotify_client.start_playback(
                            device_id=active_device['id'],
                            context_uri=f"spotify:playlist:{current_playlist_id}",
                            offset={"position": message.position}
                        )
                    else:
                        # Otherwise fall back to searching for the track in the playlist
                        playlist = self.auth.spotify_client.playlist(current_playlist_id)
                        track_uris = [track['track']['uri'] for track in playlist['tracks']['items'] if track['track']]
                        
                        try:
                            track_index = track_uris.index(f"spotify:track:{message.result_id}")
                            self.auth.spotify_client.start_playback(
                                device_id=active_device['id'],
                                context_uri=f"spotify:playlist:{current_playlist_id}",
                                offset={"position": track_index}
                            )
                        except ValueError:
                            # Track not found in current playlist, play individually
                            self.auth.spotify_client.start_playback(
                                device_id=active_device['id'],
                                uris=[f"spotify:track:{message.result_id}"]
                            )
                else:
                    # No playlist context or in Liked Songs, play track directly
                    self.auth.spotify_client.start_playback(
                        device_id=active_device['id'],
                        uris=[f"spotify:track:{message.result_id}"]
                    )
            except Exception as e:
                self.notify(f"Playback error: {str(e)}", severity="error")

    def action_focus_search(self) -> None:
        search_input = self.query_one("Input")
        search_input.focus()

    def action_refresh(self) -> None:
        if self.auth.spotify_client:
            library_section = self.query_one(LibrarySection)
            library_section.load_playlists(self.auth.spotify_client)
            
            playlist_view = self.query_one(PlaylistView)
            if playlist_view.current_playlist_id:
                playlist_view.load_playlist(self.auth.spotify_client, playlist_view.current_playlist_id)