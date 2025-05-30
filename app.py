from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import List, Dict, Any, Optional
from plugins import register_plugins

# Initialize FastAPI app
app = FastAPI(
    title="Juggernaut Bot API",
    description="Backend API for the Juggernaut Bot system with plugin architecture",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all plugins
app = register_plugins(app)

# Plugin registry
plugins = {}

# Models
class PluginBase(BaseModel):
    name: str
    description: str
    version: str
    enabled: bool = True

class PluginRegister(PluginBase):
    endpoints: List[str]
    config: Dict[str, Any] = {}

class PluginResponse(PluginBase):
    id: str
    status: str = "registered"

class EventModel(BaseModel):
    event_type: str
    source: str
    data: Dict[str, Any]

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Juggernaut Bot API", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# Plugin management endpoints
@app.post("/plugins/register", response_model=PluginResponse)
async def register_plugin(plugin: PluginRegister):
    plugin_id = f"{plugin.name.lower().replace(' ', '_')}"
    
    if plugin_id in plugins:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plugin with name '{plugin.name}' already registered"
        )
    
    plugins[plugin_id] = {
        **plugin.dict(),
        "id": plugin_id
    }
    
    return {**plugins[plugin_id], "status": "registered"}

@app.get("/plugins", response_model=List[PluginResponse])
async def get_plugins():
    return [PluginResponse(**plugin) for plugin in plugins.values()]

@app.get("/plugins/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str):
    if plugin_id not in plugins:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin with id '{plugin_id}' not found"
        )
    
    return PluginResponse(**plugins[plugin_id])

@app.delete("/plugins/{plugin_id}")
async def unregister_plugin(plugin_id: str):
    if plugin_id not in plugins:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin with id '{plugin_id}' not found"
        )
    
    del plugins[plugin_id]
    return {"message": f"Plugin '{plugin_id}' unregistered successfully"}

# Event bus endpoint
@app.post("/events")
async def publish_event(event: EventModel):
    # In a real implementation, this would publish to an event bus
    # For now, we'll just return the event
    return {"status": "published", "event": event.dict()}

# Main entry point
if __name__ == "__main__":
    # Get port from environment variable or use 8080 as default
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
