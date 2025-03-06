import asyncio
import json
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Static
from textual.worker import get_current_worker

from ...core.database.ticked_db import CalendarDB


class SpotifyCallbackHandler(BaseHTTPRequestHandler):
    callback_received = False
    auth_code = None

    def do_GET(self):
        if "/callback" in self.path:
            query_components = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query
            )
            SpotifyCallbackHandler.auth_code = query_components.get("code", [None])[0]
            SpotifyCallbackHandler.callback_received = True
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
            threading.Thread(target=self.server.shutdown).start()


def start_auth_server():
    server = HTTPServer(("localhost", 8888), SpotifyCallbackHandler)
    server.serve_forever()


def load_spotify_credentials():
    config_path = Path.home() / ".spotify_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                return data.get("client_id", ""), data.get("client_secret", "")
        except:
            return "", ""
    return "", ""


def save_spotify_credentials(client_id: str, client_secret: str) -> None:
    config_path = Path.home() / ".spotify_config.json"
    with open(config_path, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f)


class SpotifyAuth:
    def __init__(self, db: CalendarDB):
        self.db = db
        client_id, client_secret = load_spotify_credentials()
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = "http://localhost:8888/callback"
        self.scope = " ".join(
            [
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
                "playlist-read-collaborative",
            ]
        )

        if self.client_id and self.client_secret:
            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
            )
            self.spotify_client = None
            self._try_restore_session()
        else:
            self.sp_oauth = None
            self.spotify_client = None

    def _try_restore_session(self) -> bool:
        stored_tokens = self.db.get_spotify_tokens()
        if not stored_tokens:
            return False

        expiry = datetime.fromisoformat(stored_tokens["token_expiry"])
        if expiry > datetime.now():
            self.spotify_client = spotipy.Spotify(auth=stored_tokens["access_token"])
            return True

        try:
            token_info = self.sp_oauth.refresh_access_token(
                stored_tokens["refresh_token"]
            )
            if token_info:
                self.spotify_client = spotipy.Spotify(auth=token_info["access_token"])
                self.db.save_spotify_tokens(
                    token_info["access_token"],
                    token_info["refresh_token"],
                    datetime.now() + timedelta(seconds=token_info["expires_in"]),
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
                token_info = self.sp_oauth.get_access_token(
                    SpotifyCallbackHandler.auth_code
                )
                if token_info:
                    self.spotify_client = spotipy.Spotify(
                        auth=token_info["access_token"]
                    )
                    self.db.save_spotify_tokens(
                        token_info["access_token"],
                        token_info["refresh_token"],
                        datetime.now() + timedelta(seconds=token_info["expires_in"]),
                    )
                    return True
            except Exception as e:
                print(f"Authentication error: {e}")
                return False
        return False


class SpotifyLoginMessage(Message):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        super().__init__()


class SpotifyLogin(Widget):
    def compose(self) -> ComposeResult:
        client_id, client_secret = load_spotify_credentials()
        yield Vertical(
            Static("Spotify Login", classes="headerS"),
            Static(
                "Enter your Spotify Client ID and Secret to connect.",
                classes="description",
            ),
            Input(placeholder="Client ID", id="client_id", value=client_id),
            Input(
                placeholder="Client Secret",
                id="client_secret",
                password=True,
                value=client_secret,
            ),
            Static("How to get your Spotify credentials:", classes="help1"),
            Static("1. Go to https://developer.spotify.com/dashboard", classes="help"),
            Static("2. Log in and create a new app", classes="help"),
            Static(
                "3. Go to your Dashboard, then your settings, and copy the Client ID and Client Secret",
                classes="help",
            ),
            Static(
                "4. In the settings of your App, add http://localhost:8888/callback to Redirect URIs",
                classes="help",
            ),
            Button("Connect", variant="primary", id="login"),
            classes="login-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            client_id = self.query_one("#client_id", Input)
            client_secret = self.query_one("#client_secret", Input)
            if client_id.value and client_secret.value:
                save_spotify_credentials(client_id.value, client_secret.value)
                self.post_message(
                    SpotifyLoginMessage(client_id.value, client_secret.value)
                )
            else:
                self.notify("Please enter both Client ID and Secret", severity="error")


class SpotifyPlayer(Container):
    def notify_current_track(self, spotify_client):
        try:
            current = spotify_client.current_playback()
            if current and current.get("item"):
                track = current["item"]
                artist_names = ", ".join(artist["name"] for artist in track["artists"])
                self.notify(f"Now playing - {track['name']} by {artist_names}")
        except Exception as e:
            print(f"Error getting track info: {e}")

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Play/Pause", id="play-pause"),
            Button("Previous", id="prev-track"),
            Button("Next", id="next-track"),
        )

    @work
    async def on_button_pressed(self, event: Button.Pressed):
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            self.notify("No Spotify client available", severity="error")
            return

        try:
            current_playback = spotify_client.current_playback()

            if not current_playback:
                self.notify(
                    "No active playback found. Start playing something first.",
                    severity="error",
                )
                return

            context = current_playback.get("context")

            if event.button.id == "play-pause":
                event.stop()
                try:
                    if current_playback["is_playing"]:
                        spotify_client.pause_playback()
                        self.notify("Paused")
                    else:
                        spotify_client.start_playback()
                        self.notify_current_track(spotify_client)
                except Exception as e:
                    print(f"Playback error: {str(e)}")
                    self.notify("Error controlling playback", severity="error")

            elif event.button.id == "next-track":
                event.stop()
                try:
                    if not context:
                        self.notify(
                            "No playlist context found. Try selecting a track from a playlist.",
                            severity="warning",
                        )
                        return
                    spotify_client.next_track()
                    await asyncio.sleep(0.5)
                    self.notify_current_track(spotify_client)
                except Exception as e:
                    print(f"Next track error: {str(e)}")
                    self.notify("Error skipping to next track", severity="error")

            elif event.button.id == "prev-track":
                event.stop()
                try:
                    if not context:
                        self.notify(
                            "No playlist context found. Try selecting a track from a playlist.",
                            severity="warning",
                        )
                        return
                    spotify_client.previous_track()
                    await asyncio.sleep(0.5)
                    self.notify_current_track(spotify_client)
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
            classes="search-container",
        )


class SearchResult(Static):
    class Selected(Message):
        def __init__(
            self, result_id: str, result_type: str, position: int = None
        ) -> None:
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
        position: int = None,
    ) -> None:
        super().__init__()
        self.title = title
        self.result_id = result_id
        self.result_type = result_type
        self.artist = artist
        self.position = position

    def compose(self) -> ComposeResult:
        self.classes = "spotify-track-button"
        if self.result_type == "track":
            yield Static(f"🎵 {self.title} - {self.artist}")
        else:
            yield Static(f"📁 {self.title}")

    def on_click(self) -> None:
        self.post_message(
            self.Selected(self.result_id, self.result_type, self.position)
        )


class LibrarySection(Container):
    def compose(self) -> ComposeResult:
        yield ScrollableContainer(id="playlists-container", classes="playlists-scroll")

    def load_playlists(self, spotify_client):
        if spotify_client:
            try:
                spotify_client.current_user()
                playlists = spotify_client.current_user_playlists()

                container = self.query_one("#playlists-container")
                container.remove_children()

                container.mount(Static("Your Library", classes="section-header-lib"))
                container.mount(Static("Playlists", classes="subsection-header"))
                container.mount(PlaylistItem("Liked Songs", "liked_songs"))

                for playlist in playlists["items"]:
                    name = playlist["name"] if playlist["name"] else "Untitled Playlist"
                    container.mount(PlaylistItem(name, playlist["id"]))
                return True

            except spotipy.exceptions.SpotifyException as e:
                container = self.query_one("#playlists-container")
                container.mount(Static("⚠️ Spotify API error", classes="error-message"))
                return False

            except Exception as e:
                container = self.query_one("#playlists-container")
                container.mount(
                    Static("⚠️ Error loading playlists", classes="error-message")
                )
                return False
        else:
            return False


class RecentlyPlayedView(Container):
    def compose(self) -> ComposeResult:
        yield Static(
            "Recently Played", id="recently-played-title", classes="content-header-cont"
        )
        yield ScrollableContainer(
            id="recently-played-container", classes="tracks-scroll"
        )

    def load_recent_tracks(self, spotify_client) -> None:
        if not spotify_client:
            self.notify("No spotify client")
            return

        try:
            results = spotify_client.current_user_recently_played(limit=20)
            tracks_container = self.query_one("#recently-played-container")
            if tracks_container:
                tracks_container.remove_children()

                for i, item in enumerate(results["items"]):
                    track = item["track"]
                    artist_names = ", ".join(
                        artist["name"] for artist in track["artists"]
                    )
                    tracks_container.mount(
                        SearchResult(
                            track["name"],
                            track["id"],
                            "track",
                            artist_names,
                            position=i,
                        )
                    )
        except Exception as e:
            self.notify(f"Error loading recent tracks: {str(e)}")
            self.query_one("#recently-played-title").update(
                "Error loading recent tracks"
            )


class PlaylistView(Container):
    def __init__(self) -> None:
        super().__init__()
        self.current_playlist_id = None

    def compose(self) -> ComposeResult:
        yield Static(
            "Select a playlist", id="playlist-title", classes="content-header-cont"
        )
        yield ScrollableContainer(id="tracks-container", classes="tracks-scroll")

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
                for i, item in enumerate(results["items"]):
                    track_info = item["track"]
                    artist_names = ", ".join(
                        artist["name"] for artist in track_info["artists"]
                    )
                    tracks_container.mount(
                        SearchResult(
                            track_info["name"],
                            track_info["id"],
                            "track",
                            artist_names,
                            position=i,
                        )
                    )
            else:
                playlist = spotify_client.playlist(playlist_id)
                self.query_one("#playlist-title").update(playlist["name"])
                for i, item in enumerate(playlist["tracks"]["items"]):
                    track_info = item["track"]
                    if track_info:
                        artist_names = ", ".join(
                            artist["name"] for artist in track_info["artists"]
                        )
                        tracks_container.mount(
                            SearchResult(
                                track_info["name"],
                                track_info["id"],
                                "track",
                                artist_names,
                                position=i,
                            )
                        )
        except Exception as e:
            print(f"Error loading playlist: {e}")
            self.query_one("#playlist-title").update("Error loading playlist")


class SearchView(Container):
    def compose(self) -> ComposeResult:
        yield Static("Search", id="search-title", classes="content-header-cont")
        yield Input(
            placeholder="Search tracks and playlists...",
            id="search-input",
            classes="search-input",
        )
        yield Container(
            Static("Results", classes="results-section-header"),
            ScrollableContainer(id="search-results-container", classes="tracks-scroll"),
            classes="search-results-area",
        )

    def on_mount(self) -> None:
        self._search_id = 0
        self._current_worker = None

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()

        if not query:
            results_container = self.query_one("#search-results-container")
            if results_container:
                results_container.remove_children()
            return
        self._search_id += 1
        self.run_search(query, self._search_id)

    @work
    async def run_search(self, query: str, search_id: int) -> None:
        await asyncio.sleep(0.5)

        if search_id != self._search_id:
            return
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            return
        worker = get_current_worker()

        try:
            results = spotify_client.search(q=query, type="track,playlist", limit=10)

            if worker.is_cancelled:
                return

            results_container = self.query_one("#search-results-container")
            if results_container:
                results_container.remove_children()
                if results.get("tracks", {}).get("items"):
                    for track in results["tracks"]["items"]:
                        if worker.is_cancelled:
                            return
                        results_container.mount(
                            SearchResult(
                                track["name"],
                                track["id"],
                                "track",
                                ", ".join(
                                    artist["name"] for artist in track["artists"]
                                ),
                            )
                        )
                if results.get("playlists", {}).get("items"):
                    for playlist in results["playlists"]["items"]:
                        if worker.is_cancelled:
                            return
                        results_container.mount(
                            SearchResult(playlist["name"], playlist["id"], "playlist")
                        )
        except spotipy.exceptions.SpotifyException as e:
            if not worker.is_cancelled and search_id == self._search_id:
                print(f"Spotify API error during search: {str(e)}")
                self.app.notify("Unable to complete search", severity="error")
        except Exception as e:
            if not worker.is_cancelled and search_id == self._search_id:
                print(f"Non-critical search error (handled): {str(e)}")


class MainContent(Container):
    def compose(self) -> ComposeResult:
        yield Container(PlaylistView(), classes="playlist-view")
        yield Container(RecentlyPlayedView(), classes="recently-played-view")
        yield Container(SearchView(), classes="search-view")

    def on_mount(self) -> None:
        if self.app.get_spotify_client():
            recently_played = self.query_one(RecentlyPlayedView)
            if recently_played:
                recently_played.load_recent_tracks(self.app.get_spotify_client())


class SpotifyView(Container):
    BINDINGS = [
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.auth = SpotifyAuth(self.app.db)
        if self.auth.spotify_client:
            self.app.set_spotify_auth(self.auth)
            self.call_after_refresh = True
        else:
            self.call_after_refresh = False

    def on_mount(self) -> None:
        self._search_id = 0
        if self.call_after_refresh:
            library_section = self.query_one(LibrarySection)
            library_section.load_playlists(self.auth.spotify_client)

    def compose(self) -> ComposeResult:
        if not self.auth.spotify_client:
            yield SpotifyLogin()
        else:
            yield SpotifyPlayer()
        yield Container(
            Static(
                f"Spotify - {'Connected 🟢' if self.auth.spotify_client else 'Not Connected 🔴'}",
                id="status-bar-title",
                classes="status-item",
            ),
            classes="status-bar",
        )
        yield Container(
            Container(
                Container(LibrarySection(), classes="playlists-section"),
                Container(
                    Static("Instructions", classes="section-title"),
                    Static("CTRL+R: Refresh", classes="instruction-item"),
                    Static("Space: Play/Pause", classes="instruction-item"),
                    Button(
                        "Authenticate Spotify",
                        id="auth-btn",
                        variant="primary",
                        classes="connect-spotify-button",
                    ),
                    classes="instructions-section",
                ),
                classes="sidebar",
            ),
            Container(MainContent(), classes="main-content"),
            classes="spotify-container",
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
            token_info = self.auth.sp_oauth.get_access_token(
                SpotifyCallbackHandler.auth_code
            )
            if token_info:
                self.auth.spotify_client = spotipy.Spotify(
                    auth=token_info["access_token"]
                )

                # Remove SpotifyLogin and mount the new UI components
                login_widget = self.query_one(SpotifyLogin)
                if login_widget:
                    login_widget.remove()

                # Mount the player and new container structure
                self.mount(SpotifyPlayer())
                self.mount(
                    Container(
                        Static(
                            "Spotify - Connected 🟢",
                            id="status-bar-title",
                            classes="status-item",
                        ),
                        classes="status-bar",
                    )
                )
                self.mount(
                    Container(
                        Container(
                            Container(LibrarySection(), classes="playlists-section"),
                            Container(
                                Static("Instructions", classes="section-title"),
                                Static("CTRL+R: Refresh", classes="instruction-item"),
                                Static("Space: Play/Pause", classes="instruction-item"),
                                Button(
                                    "Authenticate Spotify",
                                    id="auth-btn",
                                    variant="primary",
                                    classes="connect-spotify-button",
                                ),
                                classes="instructions-section",
                            ),
                            classes="sidebar",
                        ),
                        Container(MainContent(), classes="main-content"),
                        classes="spotify-container",
                    )
                )

                library_section = self.query_one(LibrarySection)
                library_section.load_playlists(self.auth.spotify_client)

                main_content = self.query_one(MainContent)
                recently_played = main_content.query_one(RecentlyPlayedView)
                if recently_played:
                    recently_played.load_recent_tracks(self.auth.spotify_client)

                self.notify("Successfully connected to Spotify!")
            else:
                self.notify("Failed to authenticate with Spotify", severity="error")
                status_bar = self.query_one("#status-bar-title")
                status_bar.update("Spotify - Not Connected 🔴")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            self.notify("Failed to authenticate with Spotify", severity="error")
            status_bar = self.query_one("#status-bar-title")
            status_bar.update("Spotify - Not Connected 🔴")

    def action_authenticate(self):
        self.do_auth()

    def get_spotify_client(self):
        return self.auth.spotify_client

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self.auth.spotify_client:
            return

        query = event.value.strip()
        if not query:
            try:
                results_container = self.query_one(SearchResult).query_one(
                    "#search-results-container"
                )
                if results_container:
                    results_container.remove_children()
            except:
                pass
            return

        self._search_id += 1
        self.run_search(query, self._search_id)

    @work
    async def run_search(self, query: str, search_id: int) -> None:
        await asyncio.sleep(0.5)

        if search_id != self._search_id:
            return
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            return
        worker = get_current_worker()

        try:
            results = spotify_client.search(q=query, type="track,playlist", limit=10)

            if worker.is_cancelled:
                return

            results_container = self.query_one("#search-results-container")
            if results_container:
                results_container.remove_children()
                if results.get("tracks", {}).get("items"):
                    for track in results["tracks"]["items"]:
                        if worker.is_cancelled:
                            return
                        results_container.mount(
                            SearchResult(
                                track["name"],
                                track["id"],
                                "track",
                                ", ".join(
                                    artist["name"] for artist in track["artists"]
                                ),
                            )
                        )
                if results.get("playlists", {}).get("items"):
                    for playlist in results["playlists"]["items"]:
                        if worker.is_cancelled:
                            return
                        results_container.mount(
                            SearchResult(playlist["name"], playlist["id"], "playlist")
                        )
        except Exception as e:
            if not worker.is_cancelled and search_id == self._search_id:
                print(f"Search error: {str(e)}")

    def on_playlist_item_selected(self, message: PlaylistItem.Selected) -> None:
        playlist_view = self.query_one(PlaylistView)
        playlist_view.load_playlist(self.auth.spotify_client, message.playlist_id)

    @work
    async def on_search_result_selected(self, message: SearchResult.Selected) -> None:
        if message.result_type == "playlist":
            playlist_view = self.query_one(PlaylistView)
            playlist_view.load_playlist(self.auth.spotify_client, message.result_id)
        elif message.result_type == "track":
            try:
                devices = self.auth.spotify_client.devices()
                if not devices["devices"]:
                    self.notify(
                        "No Spotify devices found. Please open Spotify on any device.",
                        severity="error",
                    )
                    return

                active_device = next(
                    (d for d in devices["devices"] if d["is_active"]),
                    devices["devices"][0],
                )

                playlist_view = self.query_one(PlaylistView)
                current_playlist_id = playlist_view.current_playlist_id

                if current_playlist_id and current_playlist_id != "liked_songs":
                    if message.position is not None:
                        self.auth.spotify_client.start_playback(
                            device_id=active_device["id"],
                            context_uri=f"spotify:playlist:{current_playlist_id}",
                            offset={"position": message.position},
                        )
                        await asyncio.sleep(0.5)
                        current = self.auth.spotify_client.current_playback()
                        if current and current.get("item"):
                            track = current["item"]
                            artist_names = ", ".join(
                                artist["name"] for artist in track["artists"]
                            )
                            self.notify(
                                f"Now playing - {track['name']} by {artist_names}"
                            )
                    else:
                        playlist = self.auth.spotify_client.playlist(
                            current_playlist_id
                        )
                        track_uris = [
                            track["track"]["uri"]
                            for track in playlist["tracks"]["items"]
                            if track["track"]
                        ]

                        try:
                            track_index = track_uris.index(
                                f"spotify:track:{message.result_id}"
                            )
                            self.auth.spotify_client.start_playback(
                                device_id=active_device["id"],
                                context_uri=f"spotify:playlist:{current_playlist_id}",
                                offset={"position": track_index},
                            )
                            await asyncio.sleep(0.5)
                            current = self.auth.spotify_client.current_playback()
                            if current and current.get("item"):
                                track = current["item"]
                                artist_names = ", ".join(
                                    artist["name"] for artist in track["artists"]
                                )
                                self.notify(
                                    f"Now playing - {track['name']} by {artist_names}"
                                )
                        except ValueError:
                            self.auth.spotify_client.start_playback(
                                device_id=active_device["id"],
                                uris=[f"spotify:track:{message.result_id}"],
                            )
                            await asyncio.sleep(0.5)
                            current = self.auth.spotify_client.current_playback()
                            if current and current.get("item"):
                                track = current["item"]
                                artist_names = ", ".join(
                                    artist["name"] for artist in track["artists"]
                                )
                                self.notify(
                                    f"Now playing - {track['name']} by {artist_names}"
                                )
                else:
                    self.auth.spotify_client.start_playback(
                        device_id=active_device["id"],
                        uris=[f"spotify:track:{message.result_id}"],
                    )
                    await asyncio.sleep(0.5)
                    current = self.auth.spotify_client.current_playback()
                    if current and current.get("item"):
                        track = current["item"]
                        artist_names = ", ".join(
                            artist["name"] for artist in track["artists"]
                        )
                        self.notify(f"Now playing - {track['name']} by {artist_names}")
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
                playlist_view.load_playlist(
                    self.auth.spotify_client, playlist_view.current_playlist_id
                )

            main_content = self.query_one(MainContent)
            recently_played = main_content.query_one(RecentlyPlayedView)
            if recently_played:
                recently_played.load_recent_tracks(self.auth.spotify_client)

    def on_spotify_login_message(self, message: SpotifyLoginMessage) -> None:
        save_spotify_credentials(message.client_id, message.client_secret)
        self.auth = SpotifyAuth(self.app.db)
        self.action_authenticate()
