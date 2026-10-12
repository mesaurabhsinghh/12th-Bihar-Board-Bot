from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
import time
import urllib.request
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

def run_auto_pinger(port: int):
    """
    Pings the server every 8 minutes to prevent Render free tier from spinning down (15 min sleep timeout).
    Uses RENDER_EXTERNAL_URL if available, else localhost.
    """
    time.sleep(30) # Initial wait for server to start
    external_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    target_url = external_url if external_url else f"http://127.0.0.1:{port}/"
    
    logger.info(f"Auto-pinger started with target: {target_url}")
    while True:
        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "BiharBoardBot-KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Self-ping successful: {target_url} (HTTP 200)")
        except Exception as e:
            logger.warning(f"Self-ping notice: {e}")
        time.sleep(480) # Ping every 8 minutes

def start_keep_alive():
    """Starts background web server and auto-pinger daemon threads so Render never sleeps."""
    port = int(os.environ.get("PORT", "8080"))
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    
    pinger = threading.Thread(target=run_auto_pinger, args=(port,), daemon=True)
    pinger.start()
