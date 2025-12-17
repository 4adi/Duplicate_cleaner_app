import subprocess
import sys
import os
import time
import webbrowser

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    process = subprocess.Popen([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.port=8501"
    ])

    # Give Streamlit time to start
    time.sleep(3)

    # Auto-open browser
    webbrowser.open("http://localhost:8501")

    process.wait()

if __name__ == "__main__":
    main()
