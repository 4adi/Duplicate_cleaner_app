import subprocess
import sys
import os

def main():
    # Handle PyInstaller frozen EXE vs normal Python
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.headless=false",
            "--browser.gatherUsageStats=false",
            "--server.enableCORS=false",
        ]
    )

if __name__ == "__main__":
    main()
