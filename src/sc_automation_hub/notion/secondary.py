"""Secondary Notion Integration Client.

This module provides utility interfaces to interact with the secondary Notion API instance via the
`notion_client` SDK. It handles credentials retrieval, query filtering (specifically for paginated
data sources queries), date parsing, and updating page attributes in the tasks database.
"""

import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from notion_client import Client

# Load environment configuration variables
load_dotenv()

# Read authorization token and tasks data source ID from the environment for secondary instance
NOTION_SECONDARY_TOKEN = os.getenv("NOTION_SECONDARY_TOKEN")
NOTION_SECONDARY_TASKS_ID = os.getenv("NOTION_SECONDARY_TASKS_ID")


def _get_notion_client() -> Client:
  """Retrieves and instantiates the secondary Notion Client.

  Returns:
      An authenticated instance of the notion_client.Client.

  Raises:
      ValueError: If `NOTION_SECONDARY_TOKEN` is not defined in the environment.
  """
  if not NOTION_SECONDARY_TOKEN:
    raise ValueError("NOTION_SECONDARY_TOKEN is not set in the environment variables.")

  return Client(auth=NOTION_SECONDARY_TOKEN)


def _get_tasks_data_source_id() -> str:
  """Retrieves the secondary Notion database or data source ID.

  Returns:
      The string database identifier.

  Raises:
      ValueError: If `NOTION_SECONDARY_TASKS_ID` is not defined in the environment.
  """
  if not NOTION_SECONDARY_TASKS_ID:
    raise ValueError("NOTION_SECONDARY_TASKS_ID is not set in the environment variables.")

  return NOTION_SECONDARY_TASKS_ID


def _fetch_tasks_with_filter(filter_dict: dict) -> list[dict]:
  """Fetches tasks from secondary Notion with the given filter, supporting pagination.

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
  """Fetches secondary recurring tasks that need to be updated.

  Queries for tasks where the "Due date" property is empty AND the
  "Do it in # days" property is set.

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
        "property": "Do it in # days",
        "number": {
          "is_not_empty": True,
        }
      }
    ]
  }
  
  return _fetch_tasks_with_filter(filter_dict)


def update_task_due_date(task: dict):
  """Computes and updates the due date of a task in secondary Notion.

  Calculates the new due date as: `today` + `Do it in # days` (in days).
  After setting the new "Due date", it clears the "Do it in # days" field.

  Args:
      task: A dictionary containing the page object structure returned by Notion.

  Raises:
      ValueError: If "Do it in # days" property is missing or invalid.
  """
  task_id = task.get("id")
  notion = _get_notion_client()
  properties = task.get("properties", {})
  offset_property = properties.get("Do it in # days", {})

  offset_days = offset_property.get("number")
  if offset_days is None:
    raise ValueError(f"Cannot update task {task_id}: missing 'Do it in # days' value.")
  
  # Calculate new due date starting from today
  today = date.today()
  new_due_date = (today + timedelta(days=int(offset_days))).isoformat()
  
  # Update page properties in Notion database
  notion.pages.update(
    page_id=task_id,
    properties={
      "Due date": {
        "date": {
          "start": new_due_date
        }
      },
      "Do it in # days": {
        "number": None  # Clear the offset so it is not processed again
      }
    }
  )
