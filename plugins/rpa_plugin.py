import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import playwright.async_api as pw
import asyncio
import base64
import json

# Models
class TaskConfig(BaseModel):
    name: str
    description: str
    target_url: Optional[str] = None
    steps: List[Dict[str, Any]]
    schedule: Optional[Dict[str, Any]] = None

class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None

# Router
router = APIRouter(
    prefix="/rpa",
    tags=["RPA Plugin"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage for tasks and results
tasks = {}
results = {}

@router.post("/tasks", response_model=Dict[str, str])
async def create_task(task_config: TaskConfig):
    """Create a new RPA task"""
    task_id = f"task_{len(tasks) + 1}"
    tasks[task_id] = task_config.dict()
    return {"task_id": task_id, "status": "created"}

@router.get("/tasks", response_model=Dict[str, List[Dict[str, Any]]])
async def get_tasks():
    """Get all RPA tasks"""
    return {"tasks": [{"id": k, **v} for k, v in tasks.items()]}

@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task(task_id: str):
    """Get a specific RPA task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    return {"id": task_id, **tasks[task_id]}

@router.post("/tasks/{task_id}/execute", response_model=TaskStatus)
async def execute_task(task_id: str):
    """Execute an RPA task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    # Start task execution in background
    asyncio.create_task(run_automation(task_id))
    
    return {
        "task_id": task_id,
        "status": "running",
        "progress": 0.0,
        "message": "Task execution started"
    }

@router.get("/tasks/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of an RPA task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    if task_id in results:
        status_value = "completed" if results[task_id].get("error") is None else "failed"
        return {
            "task_id": task_id,
            "status": status_value,
            "progress": 1.0,
            "message": "Task execution completed" if status_value == "completed" else results[task_id].get("error")
        }
    
    return {
        "task_id": task_id,
        "status": "running",
        "progress": 0.5,  # This would be updated in a real implementation
        "message": "Task is still running"
    }

@router.get("/tasks/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: str):
    """Get the result of an RPA task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    if task_id not in results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Results for task {task_id} not found. Task may still be running."
        )
    
    return {
        "task_id": task_id,
        "status": "completed" if results[task_id].get("error") is None else "failed",
        "result": results[task_id].get("result"),
        "error": results[task_id].get("error")
    }

async def run_automation(task_id: str):
    """Run the automation task using Playwright"""
    task = tasks[task_id]
    
    try:
        # Initialize Playwright
        async with pw.async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the target URL if provided
            if task.get("target_url"):
                await page.goto(task["target_url"])
            
            # Execute each step in the task
            for step in task["steps"]:
                step_type = step.get("type")
                
                if step_type == "navigate":
                    await page.goto(step["url"])
                
                elif step_type == "click":
                    if "selector" in step:
                        await page.click(step["selector"])
                    elif "coordinates" in step:
                        x, y = step["coordinates"]
                        await page.mouse.click(x, y)
                
                elif step_type == "type":
                    await page.fill(step["selector"], step["text"])
                
                elif step_type == "select":
                    await page.select_option(step["selector"], value=step.get("value"))
                
                elif step_type == "wait":
                    if "time" in step:
                        await asyncio.sleep(step["time"])
                    elif "selector" in step:
                        await page.wait_for_selector(step["selector"])
                
                elif step_type == "screenshot":
                    screenshot = await page.screenshot()
                    # In a real implementation, we would save this to a file or database
                    # For now, we'll just encode it to base64
                    encoded_image = base64.b64encode(screenshot).decode('utf-8')
                    step["result"] = {"screenshot": encoded_image}
                
                elif step_type == "extract":
                    if "selector" in step:
                        element = await page.query_selector(step["selector"])
                        if element:
                            text = await element.text_content()
                            step["result"] = {"text": text}
                    elif "xpath" in step:
                        elements = await page.xpath(step["xpath"])
                        if elements and len(elements) > 0:
                            texts = []
                            for element in elements:
                                text = await element.text_content()
                                texts.append(text)
                            step["result"] = {"texts": texts}
            
            # Close the browser
            await browser.close()
            
            # Store the results
            results[task_id] = {
                "result": {
                    "steps": task["steps"]  # This includes any results added during execution
                }
            }
    
    except Exception as e:
        # Store the error
        results[task_id] = {
            "error": str(e)
        }
