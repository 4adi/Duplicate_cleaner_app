import subprocess
import sys
import os
import time
import webbrowser

def main():
    # Resolve base directory correctly (EXE vs normal run)
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    # Start Streamlit server (NON-BLOCKING)
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Give Streamlit time to boot
    time.sleep(3)

    # Open browser ONCE
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    main()
