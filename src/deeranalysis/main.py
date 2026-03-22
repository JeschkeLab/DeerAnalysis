import threading
import time
import webview
import os

os.environ['PYWEBVIEW_GUI'] = 'cocoa'  # force macOS backend
os.environ['DEERANALYSIS_PYWEBVIEW'] = '1'                         
PORT = 8050

from deeranalysis.app import app


SPLASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #1a1a2e;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #ffffff;
        }
        .logo {
            font-size: 48px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 8px;
            color: #e0e0e0;
        }
        .subtitle {
            font-size: 14px;
            color: #888;
            margin-bottom: 40px;
            letter-spacing: 1px;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #4a90d9;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 16px;
        }
        .loading-text {
            font-size: 12px;
            color: #666;
            letter-spacing: 1px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="logo">DeerAnalysis</div>
    <div class="subtitle">EPR Data Analysis</div>
    <div class="spinner"></div>
    <div class="loading-text">Loading...</div>
</body>
</html>
"""

def run_dash():
    app.run(port=PORT, debug=False, use_reloader=False)

def wait_for_dash(window):
    """Poll until Dash is ready, then load the app."""
    import urllib.request
    time.sleep(1)  # initial delay to give Dash a moment to start
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