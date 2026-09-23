import http.server
import socketserver
import json
import requests
import sys
import os
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.json")
SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"

# Load SharePoint Session
session = requests.Session()
session.trust_env = False
if os.path.exists(COOKIES_PATH):
    with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
        session.cookies.update(cookies)
    print("✅ Loaded SharePoint cookies from cookies.json")
else:
    print("⚠️ Warning: cookies.json not found in directory!")

class SharePointProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/_api") or "/_api" in self.path:
            self.proxy_sharepoint("GET")
        elif self.path == "/" or self.path == "/app" or self.path.startswith("/#") or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "smart_forms_app.html"), "rb") as f:
                self.wfile.write(f.read())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/_api") or "/_api" in self.path:
            self.proxy_sharepoint("POST")
        else:
            self.send_error(404, "Not Found")

    def proxy_sharepoint(self, method):
        # Extract relative path to SharePoint
        url = SITE_URL + self.path
        headers = {}
        for h in ["Accept", "Content-Type", "X-RequestDigest", "X-HTTP-Method", "IF-MATCH"]:
            val = self.headers.get(h)
            if val:
                headers[h] = val

        data = None
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            data = self.rfile.read(content_length)

        try:
            r = session.request(method, url, headers=headers, data=data)
            self.send_response(r.status_code)
            for k, v in r.headers.items():
                if k.lower() not in ["content-encoding", "transfer-encoding", "content-length"]:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(r.content)))
            self.end_headers()
            self.wfile.write(r.content)
        except Exception as e:
            self.send_error(500, f"Proxy Error: {e}")

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SharePointProxyHandler) as httpd:
        print(f"=======================================================")
        print(f"🚀 CHUN KING 業務智慧表單伺服器已啟動！")
        print(f"🔗 請在瀏覽器開啟: http://localhost:{PORT}")
        print(f"=======================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n伺服器已停止。")
