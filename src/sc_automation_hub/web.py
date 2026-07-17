"""Web Application Router and Setup.

This module configures the FastAPI web application, serves the Jinja2 HTML templates,
mounts static assets, defines API endpoints to query and execute background jobs,
and handles the application startup/shutdown lifecycle events.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sc_automation_hub.scheduler import list_jobs, run_job_now, start_scheduler, stop_scheduler


# Define base directory and paths for static assets and HTML templates
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Initialize Jinja2 HTML template renderer
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Create API version 1 router
api_v1_router = APIRouter(prefix="/api/v1")

@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manages the lifecycle of the FastAPI application.

  Starts the background scheduler during startup and stops it on shutdown.
  """
  start_scheduler()
  try:
    yield
  finally:
    stop_scheduler()


# Initialize the main FastAPI application with title and lifespan hook
app = FastAPI(title="SC Automation Hub", lifespan=lifespan)

# Mount static asset directory (CSS, JS, icons) under the /static URL prefix
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(api_v1_router)


@app.get("/", response_class=HTMLResponse)
def dashboard():
  """Renders the main Automation Hub dashboard HTML page."""
  template = templates.get_template("index.html")
  return HTMLResponse(
    template.render(
      page_title="Automation Hub",
    )
  )


@api_v1_router.get("/jobs")
def api_jobs():
  """Retrieves all registered background jobs and their current execution state."""
  jobs = list_jobs()
  return {
    "jobs": jobs,
    "running_jobs": [job for job in jobs if job["running"]],
  }


@api_v1_router.post("/jobs/{job_id}/run")
def api_run_job(job_id: str):
  """Triggers a background job to run immediately.

  Args:
      job_id: The unique identifier of the job to run.

  Returns:
      A dictionary confirming the execution was triggered.

  Raises:
      HTTPException: 404 if the job_id does not exist,
                     409 if the job is already currently running.
  """
  try:
    job = run_job_now(job_id)
  except KeyError:
    raise HTTPException(status_code=404, detail="Unknown job")
  except RuntimeError as exc:
    raise HTTPException(status_code=409, detail=str(exc))

  return {
    "message": "Job execution started.",
    "job": job,
  }