#!/bin/bash
# Double-click this file (Mac) to set up and start the ShelfLife API.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed. Get it from https://www.python.org/downloads/ and try again."; read -p "Press Enter to close"; exit 1
fi
if [ ! -d venv ]; then echo "First run: setting up (about a minute)..."; python3 -m venv venv || { read -p "Setup failed. Press Enter"; exit 1; }; fi
source venv/bin/activate
pip install -q -r requirements-dev.txt || { read -p "Install failed. Press Enter"; exit 1; }
echo ""
echo "  ShelfLife API is running!  Open:  http://127.0.0.1:8000/docs"
echo "  (Leave this window open. Press Ctrl+C to stop.)"
echo ""
( sleep 2; open "http://127.0.0.1:8000/docs" ) &
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
