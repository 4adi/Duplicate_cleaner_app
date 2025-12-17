# Duplicate_cleaner_app

# Duplicate Cleaner (Streamlit)

Utility UI for previewing and deleting duplicate MongoDB field measurements and live production records.

## Prerequisites
- Python 3.9+ and `pip`
- MongoDB connection string with access to the target databases

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install streamlit pymongo python-dateutil
```

## Run the app
```bash
streamlit run duplicate_cleaner_app.py
```

## Using the UI
- Paste your MongoDB connection URI and click “Connect to Mongo”.
- Select the companies and date range you want to process.
- Preview duplicates (dry run is on by default) to review counts and summaries.
- Turn off “Dry Run” and execute deletion only when ready.
- Download the generated ZIP backups (stored in the repo root) from the UI.

## Cleanup
- Remove the virtual environment if you no longer need it:
  ```bash
  rm -rf .venv
  ```
