"""MCP Tools for task operations.

These tools are exposed via the MCP server and used by the AI agent
to manage tasks through natural language commands.
"""

import json
from datetime import datetime
from typing import Optional, Literal
from sqlmodel import Session, select

from ..models import Task


def add_task(
    session: Session,
    user_id: str,
    title: str,
    description: Optional[str] = None,
) -> dict:
    """
    Create a new task.

    Args:
        session: Database session
        user_id: The user's ID
        title: Task title
        description: Optional task description

    Returns:
        Dict with task_id, status, and title
    """
    task = Task(
        user_id=user_id,
        title=title,
        description=description,
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    return {
        "task_id": task.id,
        "status": "created",
        "title": task.title,
    }


def list_tasks(
    session: Session,
    user_id: str,
    status: Literal["all", "pending", "completed"] = "all",
) -> list:
    """
    Retrieve tasks from the list.

    Args:
        session: Database session
        user_id: The user's ID
        status: Filter by status ("all", "pending", "completed")

    Returns:
        List of task objects
    """
    query = select(Task).where(Task.user_id == user_id)

    if status == "pending":
        query = query.where(Task.completed == False)
    elif status == "completed":
        query = query.where(Task.completed == True)

    query = query.order_by(Task.created_at.desc())
    tasks = session.exec(query).all()

    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "created_at": task.created_at.isoformat(),
        }
        for task in tasks
    ]


def complete_task(
    session: Session,
    user_id: str,
    task_id: int,
) -> dict:
    """
    Mark a task as complete.

    Args:
        session: Database session
        user_id: The user's ID
        task_id: The task ID to complete

    Returns:
        Dict with task_id, status, and title
    """
    task = session.exec(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    ).first()

    if not task:
        return {
            "task_id": task_id,
            "status": "error",
            "error": "Task not found",
        }

    task.completed = True
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()

    return {
        "task_id": task.id,
        "status": "completed",
        "title": task.title,
    }


def delete_task(
    session: Session,
    user_id: str,
    task_id: int,
) -> dict:
    """
    Remove a task from the list.

    Args:
        session: Database session
        user_id: The user's ID
        task_id: The task ID to delete

    Returns:
        Dict with task_id, status, and title
    """
    task = session.exec(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    ).first()

    if not task:
        return {
            "task_id": task_id,
            "status": "error",
            "error": "Task not found",
        }

    title = task.title
    session.delete(task)
    session.commit()

    return {
        "task_id": task_id,
        "status": "deleted",
        "title": title,
    }


def update_task(
    session: Session,
    user_id: str,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Modify task title or description.

    Args:
        session: Database session
        user_id: The user's ID
        task_id: The task ID to update
        title: New title (optional)
        description: New description (optional)

    Returns:
        Dict with task_id, status, and title
    """
    task = session.exec(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    ).first()

    if not task:
        return {
            "task_id": task_id,
            "status": "error",
            "error": "Task not found",
        }

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description

    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()

    return {
        "task_id": task.id,
        "status": "updated",
        "title": task.title,
    }


# Tool definitions for the agent
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Create a new task. Use this when the user wants to add, create, or remember something as a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the task",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional detailed description of the task",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Retrieve tasks from the list. Use this when the user wants to see, show, or list their tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["all", "pending", "completed"],
                        "description": "Filter tasks by status. 'all' shows all tasks, 'pending' shows incomplete tasks, 'completed' shows finished tasks.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as complete. Use this when the user says they finished, completed, or are done with a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to mark as complete",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Remove a task from the list. Use this when the user wants to delete, remove, or cancel a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to delete",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Modify a task's title or description. Use this when the user wants to change, update, rename, or edit a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the task",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the task",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
]


def execute_tool(
    session: Session,
    user_id: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Execute a tool by name with the given arguments."""
    tools = {
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "update_task": update_task,
    }

    if tool_name not in tools:
        return {"error": f"Unknown tool: {tool_name}"}

    # Add session and user_id to arguments
    return tools[tool_name](session=session, user_id=user_id, **arguments)
