"""Application Entry Point.

This module initializes and starts the FastAPI web server using Uvicorn.
It configures host, port, and reload behavior based on environment variables.
"""

import os
import uvicorn
from sc_automation_hub.web import app

if __name__ == "__main__":
  # Start the Uvicorn ASGI server with settings from environment variables,
  # defaulting to host 0.0.0.0 and port 8000.
  uvicorn.run(
    app,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    reload=False,
  )