from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

# Models
class Route(BaseModel):
    path: str
    methods: List[str]
    description: str
    auth_required: bool = True

class ApiConfig(BaseModel):
    name: str
    base_path: str
    routes: List[Route]
    rate_limit: Optional[Dict[str, Any]] = None
    auth_config: Optional[Dict[str, Any]] = None

class ApiResponse(BaseModel):
    api_id: str
    status: str
    message: str

# Router
router = APIRouter(
    prefix="/gateway",
    tags=["API Gateway Plugin"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage for API configurations
api_configs = {}

@router.post("/apis", response_model=ApiResponse)
async def register_api(api_config: ApiConfig):
    """Register a new API with the gateway"""
    api_id = f"{api_config.name.lower().replace(' ', '_')}"
    
    if api_id in api_configs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API with name '{api_config.name}' already registered"
        )
    
    api_configs[api_id] = api_config.dict()
    
    return {
        "api_id": api_id,
        "status": "registered",
        "message": f"API '{api_config.name}' registered successfully"
    }

@router.get("/apis", response_model=Dict[str, List[Dict[str, Any]]])
async def get_apis():
    """Get all registered APIs"""
    return {"apis": [{"id": k, **v} for k, v in api_configs.items()]}

@router.get("/apis/{api_id}", response_model=Dict[str, Any])
async def get_api(api_id: str):
    """Get a specific API configuration"""
    if api_id not in api_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API with id '{api_id}' not found"
        )
    
    return {"id": api_id, **api_configs[api_id]}

@router.delete("/apis/{api_id}", response_model=ApiResponse)
async def unregister_api(api_id: str):
    """Unregister an API from the gateway"""
    if api_id not in api_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API with id '{api_id}' not found"
        )
    
    api_name = api_configs[api_id]["name"]
    del api_configs[api_id]
    
    return {
        "api_id": api_id,
        "status": "unregistered",
        "message": f"API '{api_name}' unregistered successfully"
    }

@router.get("/docs", response_model=Dict[str, Any])
async def get_api_docs():
    """Get documentation for all registered APIs"""
    docs = {}
    
    for api_id, config in api_configs.items():
        docs[api_id] = {
            "name": config["name"],
            "base_path": config["base_path"],
            "routes": []
        }
        
        for route in config["routes"]:
            docs[api_id]["routes"].append({
                "path": route["path"],
                "methods": route["methods"],
                "description": route["description"],
                "auth_required": route["auth_required"]
            })
    
    return {"api_documentation": docs}

@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """Check the health of the API Gateway"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "registered_apis": str(len(api_configs))
    }

# This would be expanded in a real implementation to include:
# - Authentication middleware
# - Rate limiting middleware
# - Request validation
# - Response transformation
# - Logging and monitoring
# - API versioning
