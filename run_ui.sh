#!/bin/bash
set -e

echo "=========================================================="
echo " Starting Acme Corp Accounts Payable Automation UI"
echo "=========================================================="

# 1. Check or activate Python virtual environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
else
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Upgrading pip..."
    pip install --upgrade pip
fi

# 2. Ensure dependencies are satisfied
echo "Checking and installing dependencies from requirements.txt..."
pip install -q -r requirements.txt

# 3. Ensure database is initialized
if [ ! -f "data/inventory.db" ]; then
    echo "Initializing local inventory database..."
    python3 -m src.validation.db_setup
fi

# 4. Launch Streamlit UI
echo "Launching web dashboard in default browser..."
streamlit run app.py