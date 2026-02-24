#!/usr/bin/env python3
"""
MCP Server for Todo Task Operations.

This server exposes task management tools via the Model Context Protocol (MCP).
It can be run as a standalone process and communicates via stdio.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from sqlmodel import Session, create_engine, select
from datetime import datetime

# Import models
from app.models import Task


# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Create engine if DATABASE_URL is provided
engine = None
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """Get a database session."""
    if not engine:
        raise RuntimeError("Database not configured")
    return Session(engine)


# Create MCP server
server = Server("todo-mcp-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="add_task",
            description="Create a new task. Use this when the user wants to add, create, or remember something as a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the task",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional detailed description of the task",
                    },
                },
                "required": ["user_id", "title"],
            },
        ),
        Tool(
            name="list_tasks",
            description="Retrieve tasks from the list. Use this when the user wants to see, show, or list their tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["all", "pending", "completed"],
                        "description": "Filter tasks by status. 'all' shows all tasks, 'pending' shows incomplete tasks, 'completed' shows finished tasks.",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="complete_task",
            description="Mark a task as complete. Use this when the user says they finished, completed, or are done with a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to mark as complete",
                    },
                },
                "required": ["user_id", "task_id"],
            },
        ),
        Tool(
            name="delete_task",
            description="Remove a task from the list. Use this when the user wants to delete, remove, or cancel a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to delete",
                    },
                },
                "required": ["user_id", "task_id"],
            },
        ),
        Tool(
            name="update_task",
            description="Modify a task's title or description. Use this when the user wants to change, update, rename, or edit a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID",
                    },
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
                "required": ["user_id", "task_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool and return results."""
    try:
        with get_session() as session:
            user_id = arguments.get("user_id")
            if not user_id:
                return [TextContent(type="text", text=json.dumps({"error": "user_id is required"}))]

            if name == "add_task":
                task = Task(
                    user_id=user_id,
                    title=arguments["title"],
                    description=arguments.get("description"),
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                result = {
                    "task_id": task.id,
                    "status": "created",
                    "title": task.title,
                }

            elif name == "list_tasks":
                status = arguments.get("status", "all")
                query = select(Task).where(Task.user_id == user_id)

                if status == "pending":
                    query = query.where(Task.completed == False)
                elif status == "completed":
                    query = query.where(Task.completed == True)

                query = query.order_by(Task.created_at.desc())
                tasks = session.exec(query).all()

                result = [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    }
                    for task in tasks
                ]

            elif name == "complete_task":
                task_id = arguments["task_id"]
                task = session.exec(
                    select(Task).where(Task.id == task_id, Task.user_id == user_id)
                ).first()

                if not task:
                    result = {"task_id": task_id, "status": "error", "error": "Task not found"}
                else:
                    task.completed = True
                    task.updated_at = datetime.utcnow()
                    session.add(task)
                    session.commit()
                    result = {"task_id": task.id, "status": "completed", "title": task.title}

            elif name == "delete_task":
                task_id = arguments["task_id"]
                task = session.exec(
                    select(Task).where(Task.id == task_id, Task.user_id == user_id)
                ).first()

                if not task:
                    result = {"task_id": task_id, "status": "error", "error": "Task not found"}
                else:
                    title = task.title
                    session.delete(task)
                    session.commit()
                    result = {"task_id": task_id, "status": "deleted", "title": title}

            elif name == "update_task":
                task_id = arguments["task_id"]
                task = session.exec(
                    select(Task).where(Task.id == task_id, Task.user_id == user_id)
                ).first()

                if not task:
                    result = {"task_id": task_id, "status": "error", "error": "Task not found"}
                else:
                    if "title" in arguments and arguments["title"]:
                        task.title = arguments["title"]
                    if "description" in arguments:
                        task.description = arguments["description"]
                    task.updated_at = datetime.utcnow()
                    session.add(task)
                    session.commit()
                    result = {"task_id": task.id, "status": "updated", "title": task.title}

            else:
                result = {"error": f"Unknown tool: {name}"}

            return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
