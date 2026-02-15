import threading
import time
import webview
from deeranalysis.app import app

PORT = 8050

def run_dash():
    app.run(port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Dash in a separate thread
    dash_thread = threading.Thread(target=run_dash)
    dash_thread.daemon = True
    dash_thread.start()

    # Wait a moment to ensure Dash is up before opening the webview
    time.sleep(1)

    # Open the webview window pointing to the Dash app
    webview.create_window(
        title="DeerAnalysis",
        url=f"http://localhost:{PORT}",
        width=1200,
        height=800,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600),
    )   

    webview.start()