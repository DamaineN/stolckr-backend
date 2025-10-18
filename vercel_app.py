"""
Vercel handler for FastAPI backend
"""
from main import app
from mangum import Mangum

# Create the Vercel handler
handler = Mangum(app, lifespan="off")