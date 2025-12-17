import subprocess
import sys
import os
import time
import webbrowser

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    # Guard to prevent infinite browser tabs
    if os.environ.get("DUPLICATE_CLEANER_BROWSER_OPENED") != "1":
        os.environ["DUPLICATE_CLEANER_BROWSER_OPENED"] = "1"

        subprocess.Popen([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ])

        # Give server time to start
        time.sleep(2)

        # Open browser ONCE
        webbrowser.open("http://localhost:8501")

    else:
        # Streamlit re-run → do nothing
        pass


if __name__ == "__main__":
    main()
