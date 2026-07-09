import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TASKS_ID = os.getenv("NOTION_TASKS_ID")


def _get_notion_client():
  if not NOTION_TOKEN:
    raise ValueError("NOTION_TOKEN is not set in the environment variables.")

  return Client(auth=NOTION_TOKEN)


def _get_tasks_data_source_id():
  if not NOTION_TASKS_ID:
    raise ValueError("NOTION_TASKS_ID is not set in the environment variables.")

  return NOTION_TASKS_ID

def _fetch_tasks_with_filter(filter_dict):
  """Fetch tasks from Notion with the given filter."""

  results = []
  start_cursor = None
  notion = _get_notion_client()

  while True:
    query_kwargs = {
      "data_source_id": _get_tasks_data_source_id(),
      "filter": filter_dict,
    }

    if start_cursor:
      query_kwargs["start_cursor"] = start_cursor

    response = notion.data_sources.query(**query_kwargs)
    results.extend(response.get("results", []))

    if not response.get("has_more"):
      break

    start_cursor = response.get("next_cursor")

  return results

def get_recurring_tasks_to_update():
  """Fetch recurring tasks that need to be updated."""

  filter_dict = {
    "property": "Offset due date",
    "number": {
      "is_not_empty": True,
    },
  }
  
  return _fetch_tasks_with_filter(filter_dict)


def _parse_planned_start(planned_start):
  if not planned_start:
    return None

  try:
    return datetime.fromisoformat(planned_start.replace("Z", "+00:00")).date()
  except ValueError:
    return date.fromisoformat(planned_start)

def update_task_due_date(task):
  """Update the due date of a task."""
  
  task_id = task.get("id")
  notion = _get_notion_client()
  properties = task.get("properties", {})
  planned_start_property = properties.get("Planned start", {})
  offset_due_date_property = properties.get("Offset due date", {})

  planned_start = planned_start_property.get("date", {}).get("start") if planned_start_property.get("date") else None
  offset_due_date = offset_due_date_property.get("number") if offset_due_date_property.get("number") is not None else 0
  start_date = _parse_planned_start(planned_start)
  new_due_date = (start_date + timedelta(days=int(offset_due_date))).isoformat() if start_date else ""
  
  if not new_due_date:
    raise ValueError(f"Cannot update task {task_id} due to missing data.")
  
  notion.pages.update(
    page_id=task_id,
    properties={
      "Due date": {
        "date": {
          "start": new_due_date
        }
      },
      "Offset due date": {
        "number": None
      }
    }
  )