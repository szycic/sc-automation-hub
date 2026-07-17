"""Notion Integration Client.

This module provides utility interfaces to interact with the Notion API via the
`notion_client` SDK. It handles credentials retrieval, query filtering (specifically for paginated
data sources queries), date parsing, and updating page attributes in the tasks database.
"""

import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from notion_client import Client

# Load environment configuration variables
load_dotenv()

# Read authorization token and tasks data source ID from the environment
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TASKS_ID = os.getenv("NOTION_TASKS_ID")


def _get_notion_client() -> Client:
  """Retrieves and instantiates the Notion Client.

  Returns:
      An authenticated instance of the notion_client.Client.

  Raises:
      ValueError: If `NOTION_TOKEN` is not defined in the environment.
  """
  if not NOTION_TOKEN:
    raise ValueError("NOTION_TOKEN is not set in the environment variables.")

  return Client(auth=NOTION_TOKEN)


def _get_tasks_data_source_id() -> str:
  """Retrieves the Notion database or data source ID.

  Returns:
      The string database identifier.

  Raises:
      ValueError: If `NOTION_TASKS_ID` is not defined in the environment.
  """
  if not NOTION_TASKS_ID:
    raise ValueError("NOTION_TASKS_ID is not set in the environment variables.")

  return NOTION_TASKS_ID


def _fetch_tasks_with_filter(filter_dict: dict) -> list[dict]:
  """Fetches tasks from Notion with the given filter, supporting pagination.

  Args:
      filter_dict: A dictionary representation of a Notion filter structure.

  Returns:
      A list of matching task page objects retrieved from the query.
  """
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

    # Query the Notion data source with pagination
    response = notion.data_sources.query(**query_kwargs)
    results.extend(response.get("results", []))

    if not response.get("has_more"):
      break

    start_cursor = response.get("next_cursor")

  return results


def get_recurring_tasks_to_update() -> list[dict]:
  """Fetches recurring tasks that need to be updated.

  Queries for tasks where the "Due date" property is empty AND the
  "Offset due date" property is set.

  Returns:
      A list of task dictionary objects.
  """
  filter_dict = {
    "and": [
      {
        "property": "Due date",
        "date": {
          "is_empty": True,
        }
      },
      { 
        "property": "Offset due date",
        "number": {
          "is_not_empty": True,
        }
      }
    ]
  }
  
  return _fetch_tasks_with_filter(filter_dict)


def _parse_planned_start(planned_start: str | None) -> date | None:
  """Parses the 'Planned start' date string from ISO format or standard date format.

  Args:
      planned_start: The ISO string (e.g. 2026-07-17Z or 2026-07-17).

  Returns:
      A datetime.date object representing the start date, or None if input is empty.
  """
  if not planned_start:
    return None

  try:
    return datetime.fromisoformat(planned_start.replace("Z", "+00:00")).date()
  except ValueError:
    return date.fromisoformat(planned_start)


def update_task_due_date(task: dict):
  """Computes and updates the due date of a task in Notion.

  Calculates the new due date as: `Planned start` + `Offset due date` (in days).
  After setting the new "Due date", it clears the "Offset due date" field.

  Args:
      task: A dictionary containing the page object structure returned by Notion.

  Raises:
      ValueError: If either planned start date is missing or cannot calculate due date.
  """
  task_id = task.get("id")
  notion = _get_notion_client()
  properties = task.get("properties", {})
  planned_start_property = properties.get("Planned start", {})
  offset_due_date_property = properties.get("Offset due date", {})

  # Extract the start date string and offset integer
  planned_start = planned_start_property.get("date", {}).get("start") if planned_start_property.get("date") else None
  offset_due_date = offset_due_date_property.get("number") if offset_due_date_property.get("number") is not None else 0
  start_date = _parse_planned_start(planned_start)
  
  # Calculate new due date
  new_due_date = (start_date + timedelta(days=int(offset_due_date))).isoformat() if start_date else ""
  
  if not new_due_date:
    raise ValueError(f"Cannot update task {task_id} due to missing data.")
  
  # Update page properties in Notion database
  notion.pages.update(
    page_id=task_id,
    properties={
      "Due date": {
        "date": {
          "start": new_due_date
        }
      },
      "Offset due date": {
        "number": None  # Clear the offset so it is not processed again
      }
    }
  )