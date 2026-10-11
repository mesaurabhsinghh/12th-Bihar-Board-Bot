from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
import logging

logger = logging.getLogger(__name__)

class SimpleHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html_response = (
            "<!DOCTYPE html><html><head><title>12th Bihar Board Bot</title></head>"
            "<body style='font-family: Arial; text-align: center; padding-top: 50px;'>"
            "<h1 style='color: #2e7d32;'>✅ 12th Bihar Board Telegram Quiz Bot is Running 24x7!</h1>"
            "<p>Bot is actively listening for student queries on Telegram.</p>"
            "</body></html>"
        )
        self.wfile.write(html_response.encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_server(port: int):
    try:
        server_address = ("0.0.0.0", port)
        httpd = HTTPServer(server_address, SimpleHealthHandler)
        logger.info(f"Keep-alive web server running on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Keep-alive server error: {e}")

def start_keep_alive():
    """Starts the background web server in a daemon thread so Render/Koyeb never sleeps."""
    port = int(os.environ.get("PORT", "8080"))
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
