#!/bin/bash

# Start script for Render deployment

# Set default environment variables if not provided
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${PORT:-8000}
export DEBUG_MODE=${DEBUG_MODE:-"False"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

# Start the FastAPI application with uvicorn
exec uvicorn main:app --host $API_HOST --port $API_PORT --log-level info --access-log