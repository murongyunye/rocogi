"""Rocogi Windows launcher entry point.

Build with scripts/build-rocogi-windows.ps1. Starts the local FastAPI server,
waits for health, then opens the browser UI.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn


HOST = "127.0.0.1"
PORT = 8787


def wait_for_server(timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}/api/health", timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> None:
    from app.main import app

    thread = threading.Thread(
        target=lambda: uvicorn.run(app, host=HOST, port=PORT, log_level="info"),
        daemon=True,
        name="rocogi-server",
    )
    thread.start()
    if wait_for_server():
        webbrowser.open(f"http://{HOST}:{PORT}/launcher")
    else:
        print(f"Rocogi server did not become ready. Open http://{HOST}:{PORT}/launcher manually.")
    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Rocogi stopped.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        from app.main import app

        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    else:
        main()
