# SC Notion Automation
This repository contains the source code for the `sc-notion-automation` package.

The app is a small FastAPI dashboard for running Notion automation jobs, showing their current status, and triggering them manually before the next scheduled run.

It is intended for personal or local-network use and does not include production authentication or any other extra security by default. If you expose the app beyond a trusted LAN, add authentication, TLS, and restrict access to the API endpoints.

## Environment Variables
The following environment variables can be set to configure the package:

| Variable | Purpose | Example |
|---|---|---|
| `NOTION_TOKEN` | Notion integration token used to authenticate API requests | `secret_xxx` |
| `NOTION_TASKS_ID` | Notion database/data source ID containing the tasks to update | `xxxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `HOST` | Host address used by the development server | `0.0.0.0` |
| `PORT` | Port used by the development server | `8000` |

## Installation
To install the package, run:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

## Running
To run the application, execute:
```bash
PYTHONPATH=src python -m sc_notion_automation.main
```

Then open the dashboard at:
```text
http://127.0.0.1:8000
```

The API is available under the versioned prefix:
```text
/api/v1/jobs
/api/v1/jobs/{job_id}/run
```

If you want to change the bind address or port, set `HOST` and `PORT` before starting the app.
