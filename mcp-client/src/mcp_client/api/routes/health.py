"""
Health check endpoints for MCP Client API.

This module provides health monitoring and status endpoints.
"""

import os
import psutil
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database.database import get_db_session, get_database

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MCP Client API",
        "version": "0.1.0"
    }


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with system information."""
    try:
        # Database health
        db = get_database()
        db_healthy = True
        try:
            with db.session_scope() as session:
                # Simple query to test database
                session.execute("SELECT 1")
        except Exception:
            db_healthy = False
        
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MCP Client API",
            "version": "0.1.0",
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "url": db.database_url.split("://")[0] + "://***"  # Hide credentials
                },
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent
                    },
                    "disk": {
                        "total": disk.total,
                        "free": disk.free,
                        "percent": (disk.used / disk.total) * 100
                    }
                }
            },
            "environment": {
                "python_version": os.sys.version,
                "platform": os.name,
                "working_directory": os.getcwd()
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/ready")
async def readiness_check():
    """Readiness check for deployment orchestration."""
    try:
        # Check database connectivity
        db = get_database()
        with db.session_scope() as session:
            session.execute("SELECT 1")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "ready": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/live")
async def liveness_check():
    """Liveness check for deployment orchestration."""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    } 