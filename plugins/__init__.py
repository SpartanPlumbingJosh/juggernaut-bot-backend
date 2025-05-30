from fastapi import APIRouter, FastAPI
from . import rpa_plugin, api_gateway_plugin

def register_plugins(app: FastAPI):
    """Register all plugins with the FastAPI app"""
    
    # Register RPA Plugin
    app.include_router(rpa_plugin.router)
    
    # Register API Gateway Plugin
    app.include_router(api_gateway_plugin.router)
    
    # Additional plugins will be registered here as they are implemented
    
    return app
