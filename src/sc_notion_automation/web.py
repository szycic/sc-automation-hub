from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sc_notion_automation.scheduler import list_jobs, run_job_now, start_scheduler, stop_scheduler


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

api_v1_router = APIRouter(prefix="/api/v1")

@asynccontextmanager
async def lifespan(app: FastAPI):
  start_scheduler()
  try:
    yield
  finally:
    stop_scheduler()


app = FastAPI(title="SC Notion Automation", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(api_v1_router)


@app.get("/", response_class=HTMLResponse)
def dashboard():
  template = templates.get_template("index.html")
  return HTMLResponse(
    template.render(
      page_title="Notion Automation",
    )
  )


@api_v1_router.get("/jobs")
def api_jobs():
  jobs = list_jobs()
  return {
    "jobs": jobs,
    "running_jobs": [job for job in jobs if job["running"]],
  }


@api_v1_router.post("/jobs/{job_id}/run")
def api_run_job(job_id: str):
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