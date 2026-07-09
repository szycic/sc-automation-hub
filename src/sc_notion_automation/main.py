import os
import uvicorn
from sc_notion_automation.web import app

if __name__ == "__main__":
  uvicorn.run(
    app,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    reload=False,
  )