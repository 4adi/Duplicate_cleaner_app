import subprocess
import sys
import os
import time
import webbrowser
import socket

LOCK_FILE = "duplicate_cleaner.lock"
PORT = 8501


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    # ---------------- SINGLE INSTANCE LOCK ----------------
    lock_path = os.path.join(os.getenv("TEMP", "."), LOCK_FILE)

    if os.path.exists(lock_path):
        # App already running → just open browser once
        webbrowser.open(f"http://localhost:{PORT}")
        return

    with open(lock_path, "w") as f:
        f.write("locked")

    # ---------------- PATH RESOLUTION ----------------
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    # ---------------- START STREAMLIT ----------------
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            f"--server.port={PORT}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # ---------------- WAIT UNTIL SERVER IS READY ----------------
    for _ in range(30):  # ~15 seconds max
        if is_port_open(PORT):
            break
        time.sleep(0.5)

    # ---------------- OPEN BROWSER ONCE ----------------
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    main()
