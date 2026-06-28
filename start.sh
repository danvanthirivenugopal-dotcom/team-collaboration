#!/bin/bash
# Start the FastAPI backend in the background
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait a few seconds for backend to start
sleep 3

# Start the Streamlit frontend on the port provided by Railway (or 8501 default)
export PORT=${PORT:-8501}
export BACKEND_URL="http://127.0.0.1:8000"

echo "Starting Streamlit on port $PORT connecting to backend at $BACKEND_URL"
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
