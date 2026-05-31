import threading
import time
import webview
import os
import sys
from pathlib import Path

#os.environ['PYWEBVIEW_GUI'] = 'cocoa'  # force macOS backend
os.environ['DEERANALYSIS_PYWEBVIEW'] = '1'


def _find_free_port(start=8050):
    import socket
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    raise RuntimeError("No free port found in range 8050-8149")

PORT = _find_free_port()

from deeranalysis.app import app

# Close the PyInstaller splash screen (Windows only; no-op on other platforms)
try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass


def _splash_html():
    if getattr(sys, 'frozen', False):
        basedir = Path(sys._MEIPASS)
    else:
        basedir = Path(__file__).parent
    img_path = (basedir / 'assets' / 'splash.png').as_uri()
    return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
        }}
        img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img src="{img_path}" />
</body>
</html>"""

SPLASH_HTML = _splash_html()

def run_dash():
    app.run(port=PORT, debug=False, use_reloader=False)

def wait_for_dash(window):
    """Poll until Dash is ready, then load the app."""
    import urllib.request
    # time.sleep(5)  # initial delay to give Dash a moment to start
    while True:
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}", timeout=1)
            window.load_url(f"http://localhost:{PORT}")
            break
        except Exception:
            time.sleep(0.2)

if __name__ == "__main__":
    # Start Dash in a separate thread
    dash_thread = threading.Thread(target=run_dash)
    dash_thread.daemon = True
    dash_thread.start()

    # Create the window with the splash screen HTML
    window = webview.create_window(
        title="DeerAnalysis",
        html=SPLASH_HTML,
        width=1200,
        height=800,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600),
    )
    
    # Start a thread that waits for Dash and then swaps the content
    threading.Thread(target=wait_for_dash, args=(window,), daemon=True).start()

    webview.start()