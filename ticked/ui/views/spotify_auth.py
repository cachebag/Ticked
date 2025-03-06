import os
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import spotipy
from spotipy.oauth2 import SpotifyOAuth


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


class SpotifyAuth:
    def __init__(self, db):
        self.db = db
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = "http://localhost:8888/callback"
        self.scope = "user-library-read playlist-read-private user-read-private user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing streaming app-remote-control user-read-recently-played user-top-read playlist-read-collaborative"
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )
        self.spotify_client = None
        self._try_restore_session()

    def _try_restore_session(self):
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

    def start_auth(self):
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
