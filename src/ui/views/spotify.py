# spotify.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Static, Input
from textual import work
import asyncio
from textual.binding import Binding
from textual.message import Message
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import webbrowser
from dotenv import load_dotenv
import os
import threading
from .spotify_auth import start_auth_server, SpotifyCallbackHandler

load_dotenv()

class SpotifyAuth:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        self.scope = "user-library-read playlist-read-private user-read-private user-top-read"
        
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        
        self.spotify_client = None

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

class SearchResults(Container):
    def compose(self) -> ComposeResult:
        yield ScrollableContainer(id="results-container")

class LibrarySection(Container):
    def compose(self) -> ComposeResult:
        yield Button("Connect Spotify", id="auth-btn", variant="primary", classes="connect-spotify-button")
        yield ScrollableContainer(
            Static("Your Library", classes="section-header"),
            Static("Playlists", classes="subsection-header"),
            id="playlists-container"
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
        yield Static("", id="playlist-title", classes="content-header")
        yield ScrollableContainer(id="tracks-container")

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
                tracks = results['items']
                for track in tracks:
                    track_info = track['track']
                    tracks_container.mount(SearchResult(
                        track_info['name'],
                        track_info['id'],
                        'track',
                        ", ".join(artist['name'] for artist in track_info['artists'])
                    ))
            else:
                playlist = spotify_client.playlist(playlist_id)
                self.query_one("#playlist-title").update(playlist['name'])
                for track in playlist['tracks']['items']:
                    track_info = track['track']
                    if track_info:
                        tracks_container.mount(SearchResult(
                            track_info['name'],
                            track_info['id'],
                            'track',
                            ", ".join(artist['name'] for artist in track_info['artists'])
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
        self.auth = SpotifyAuth()
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            LibrarySection(),
            MainContent(),
            id="spotify-main"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-btn":
            self.notify("Starting Spotify authentication...")
            self.action_authenticate() 
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
            pass

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