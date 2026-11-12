"""Run ONCE on your Mac: gets a YouTube refresh token. Never paste the output in chat; put it only in GitHub secrets.
usage: python3 scripts/yt_get_token.py [path/to/client_secret.json]   (default: newest client_secret*.json in ~/Downloads)"""
import glob, http.server, json, os, sys, urllib.parse, urllib.request, webbrowser
path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.expanduser("~/Downloads/client_secret*.json")), key=os.path.getmtime, default=None)
if not path: sys.exit("client_secret*.json Downloads mein nahi mili. Google Cloud se OAuth client JSON download karo.")
c = json.load(open(path)); c = c.get("installed") or c.get("web")
PORT = 8765; REDIR = f"http://127.0.0.1:{PORT}"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(dict(client_id=c["client_id"], redirect_uri=REDIR,
      response_type="code", scope="https://www.googleapis.com/auth/youtube.upload", access_type="offline", prompt="consent"))
code = {}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); code.update({k: v[0] for k, v in q.items()})
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write("<h2>Ho gaya! Terminal pe wapas jao.</h2>".encode())
    def log_message(self, *a): pass
print("Browser khul raha hai. Apne YouTube channel wale Google account se login karo...")
webbrowser.open(url)
srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
while "code" not in code and "error" not in code: srv.handle_request()
if "error" in code: sys.exit("Error: " + code["error"])
data = urllib.parse.urlencode(dict(code=code["code"], client_id=c["client_id"], client_secret=c["client_secret"], redirect_uri=REDIR,
                                   grant_type="authorization_code")).encode()
tok = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", data))
if "refresh_token" not in tok: sys.exit("Refresh token nahi mila: " + json.dumps(tok))
print("\n=== Ye 3 values GitHub secrets mein daalo (chat mein mat bhejna) ===\n")
print("YT_CLIENT_ID      =", c["client_id"])
print("YT_CLIENT_SECRET  =", c["client_secret"])
print("YT_REFRESH_TOKEN  =", tok["refresh_token"])
