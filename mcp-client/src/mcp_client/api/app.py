"""
FastAPI application for MCP Client.

This module creates and configures the FastAPI application
with all necessary routes, middleware, and dependencies.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from ..database.database import init_database, get_database
from .routes import servers, queries, chat, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🚀 Starting MCP Client API...")
    
    # Initialize database
    init_database()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down MCP Client API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="MCP Client API",
        description="""
        A comprehensive API for managing Model Context Protocol (MCP) servers
        and running intelligent conversations with LLM integration.
        
        ## Features
        
        * **Server Management**: Add, configure, and manage MCP servers
        * **Query Execution**: Execute tools, read resources, and get prompts
        * **Intelligent Chat**: LLM-powered conversations with automatic tool calling
        * **Multi-Provider Support**: OpenAI, Anthropic, and AWS Bedrock integration
        * **Real-time Monitoring**: Server health and capability tracking
        
        ## Getting Started
        
        1. Add an MCP server using the `/servers/` endpoint
        2. Start a chat session using the `/chat/` endpoint
        3. Ask questions and let the AI use tools automatically
        
        ## Documentation
        
        * [MCP Specification](https://modelcontextprotocol.io/)
        * [GitHub Repository](https://github.com/your-repo/mcp-client)
        """,
        version="0.1.0",
        contact={
            "name": "MCP Client Team",
            "url": "https://github.com/your-repo/mcp-client",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(servers.router, prefix="/servers", tags=["MCP Servers"])
    app.include_router(queries.router, prefix="/queries", tags=["Queries"])
    app.include_router(chat.router, prefix="/chat", tags=["Chat"])
    
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to docs."""
        return RedirectResponse(url="/docs")
    
    @app.get("/info")
    async def app_info():
        """Get application information."""
        return {
            "name": "MCP Client API",
            "version": "0.1.0",
            "description": "REST API for Model Context Protocol client operations",
            "features": [
                "MCP Server Management",
                "Tool Execution",
                "Resource Reading", 
                "Prompt Generation",
                "LLM-powered Chat",
                "Multi-provider Support"
            ],
            "endpoints": {
                "health": "/health/",
                "servers": "/servers/",
                "queries": "/queries/",
                "chat": "/chat/",
                "docs": "/docs",
                "openapi": "/openapi.json"
            }
        }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"Starting MCP Client API on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(
        "src.mcp_client.api.app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    ) 