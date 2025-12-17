import os
import sys
import subprocess

def main():
    # Resolve correct base dir
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
        python_exe = os.path.join(base_dir, "python.exe")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        python_exe = sys.executable

    app_path = os.path.join(base_dir, "duplicate_cleaner_app.py")

    # Run Streamlit using CLI entrypoint
    subprocess.run(
        [
            python_exe,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--browser.gatherUsageStats=false",
        ],
        check=True,
    )

if __name__ == "__main__":
    main()
