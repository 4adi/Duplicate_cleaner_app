# -----------------------------
# CONFIGURATION
# -----------------------------

VENV := venv
PYTHON := python3
PIP := $(VENV)/bin/pip
STREAMLIT := $(VENV)/bin/streamlit
APP := app.py

# -----------------------------
# MAIN COMMANDS
# -----------------------------

# Create venv + install requirements
setup: $(VENV)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Setup complete."

# Run Streamlit app
run:
	$(STREAMLIT) run $(APP)

# Delete virtual environment
clean:
	rm -rf $(VENV)
	@echo "🗑 Virtual environment removed."

# Clean and reinstall everything
reinstall: clean setup


# -----------------------------
# INTERNAL (venv creation)
# -----------------------------

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	@echo "📦 Virtual environment created."

.PHONY: setup run clean reinstall
