"""
AuditLink Desktop Entry Point
- Starts FastAPI server in a background thread
- Opens PyWebView window pointing to the React build
"""
import os
import sys
import threading
import time
import socket

# ---------------------------------------------------------------------------
# Path helpers – works both in dev and when bundled by PyInstaller
# ---------------------------------------------------------------------------

def get_base_path():
    """Return the base directory (project root or PyInstaller _MEIPASS)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE = get_base_path()
DIST_DIR = os.path.join(BASE, "dist")

# ---------------------------------------------------------------------------
# FastAPI server (background thread)
# ---------------------------------------------------------------------------

def find_free_port():
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int):
    """Run uvicorn in the current thread (blocking)."""
    import uvicorn
    from backend.main import app  # noqa: E402

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def wait_for_server(port: int, timeout: float = 10.0):
    """Block until the server accepts connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    port = find_free_port()

    # Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait until the server is ready
    if not wait_for_server(port):
        print("ERROR: FastAPI server failed to start")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"

    # Try to use PyWebView for a native window
    try:
        import webview

        # If we have a built React dist, serve it; otherwise just open the API
        if os.path.isdir(DIST_DIR):
            # Serve static files from dist via a simple file handler
            window = webview.create_window(
                "AuditLink – 회계감사 일정관리",
                url=url,
                width=1400,
                height=900,
                min_size=(1024, 700),
            )
            webview.start()
        else:
            window = webview.create_window(
                "AuditLink – 회계감사 일정관리",
                url=url,
                width=1400,
                height=900,
                min_size=(1024, 700),
            )
            webview.start()
    except ImportError:
        # Fallback: open in default browser
        import webbrowser
        print(f"PyWebView not installed. Opening in browser: {url}")
        webbrowser.open(url)
        # Keep the server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
