from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

class SpotifyCallbackHandler(BaseHTTPRequestHandler):
    callback_received = False
    auth_code = None
    def do_GET(self):
        if '/callback' in self.path:
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            SpotifyCallbackHandler.auth_code = query_components.get('code', [None])[0]
            SpotifyCallbackHandler.callback_received = True
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
            threading.Thread(target=self.server.shutdown).start()

def start_auth_server():
    server = HTTPServer(('localhost',8888),SpotifyCallbackHandler)
    server.serve_forever()
