"""
MCP Server management endpoints.

This module provides CRUD operations for MCP servers
and capability discovery functionality.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from ...database.database import get_db_session, get_database
from ...database.models import (
    MCPServer, MCPServerCreate, MCPServerUpdate, MCPServerResponse, User
)
from ...client import MCPClient, MCPClientConfig
from ...llm.agent import get_agent_manager

router = APIRouter()


def get_current_user() -> User:
    """Get current user (simplified for demo - implement proper auth)."""
    db = get_database()
    return db.get_user_by_username("admin")


@router.get("/", response_model=List[MCPServerResponse])
async def list_servers(user: User = Depends(get_current_user)):
    """List all MCP servers for the current user."""
    db = get_database()
    servers = db.get_user_servers(user.id)
    return [MCPServerResponse.model_validate(server) for server in servers]


@router.post("/", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    server_data: MCPServerCreate,
    user: User = Depends(get_current_user)
):
    """Create a new MCP server configuration."""
    try:
        db = get_database()
        
        # Create server in database
        server = db.create_mcp_server(user.id, server_data.dict())
        
        # Test connection and discover capabilities
        try:
            await discover_server_capabilities(server.id)
        except Exception as e:
            # Log the error but don't fail the creation
            print(f"Warning: Could not discover capabilities for server {server.id}: {e}")
        
        return MCPServerResponse.model_validate(server)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create server: {str(e)}"
        )


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_server(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Get a specific MCP server by ID."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    if server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return MCPServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_server(
    server_id: int,
    server_data: MCPServerUpdate,
    user: User = Depends(get_current_user)
):
    """Update an MCP server configuration."""
    db = get_database()
    
    with db.session_scope() as session:
        server = session.query(MCPServer).filter(MCPServer.id == server_id).first()
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        
        if server.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update fields
        update_data = server_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(server, field, value)
        
        server.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(server)
        
        # Refresh capabilities if connection details changed
        if any(field in update_data for field in ['server_path', 'server_url', 'server_command', 'server_args']):
            try:
                await discover_server_capabilities(server_id)
            except Exception as e:
                print(f"Warning: Could not refresh capabilities for server {server_id}: {e}")
        
        return MCPServerResponse.model_validate(server)


@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Delete an MCP server configuration."""
    db = get_database()
    
    with db.session_scope() as session:
        server = session.query(MCPServer).filter(MCPServer.id == server_id).first()
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        
        if server.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Remove agent if exists
        agent_manager = get_agent_manager()
        await agent_manager.remove_agent(server_id)
        
        # Mark as inactive instead of deleting
        server.is_active = False
        server.updated_at = datetime.utcnow()
        session.commit()
    
    return {"message": "Server deleted successfully"}


@router.post("/{server_id}/discover")
async def discover_capabilities(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Discover and update server capabilities."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    if server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        capabilities = await discover_server_capabilities(server_id)
        return {
            "message": "Capabilities discovered successfully",
            "capabilities": capabilities
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to discover capabilities: {str(e)}"
        )


@router.post("/{server_id}/test")
async def test_server_connection(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Test connection to an MCP server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    if server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Test connection
        config = MCPClientConfig(
            server_command=server.server_command,
            server_args=server.server_args or [],
            server_env=server.server_env or {},
            transport_type=server.server_type,
            timeout=10,
            debug=False
        )
        
        async with MCPClient(config) as client:
            # Connect based on server configuration
            if server.server_url:
                await client.connect(server.server_url, server.server_type)
            elif server.server_path:
                await client.connect(server.server_path)
            else:
                await client.connect_stdio(
                    server.server_command,
                    server.server_args or [],
                    server.server_env or {}
                )
            
            # Basic capability check
            await client.discover_capabilities()
            
            return {
                "status": "success",
                "message": "Connection successful",
                "tools_count": len(client.available_tools),
                "resources_count": len(client.available_resources),
                "prompts_count": len(client.available_prompts),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def discover_server_capabilities(server_id: int) -> dict:
    """Discover capabilities for a server and update database."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server:
        raise ValueError("Server not found")
    
    # Create MCP client
    config = MCPClientConfig(
        server_command=server.server_command,
        server_args=server.server_args or [],
        server_env=server.server_env or {},
        transport_type=server.server_type,
        timeout=30,
        debug=False
    )
    
    async with MCPClient(config) as client:
        # Connect based on server configuration
        if server.server_url:
            await client.connect(server.server_url, server.server_type)
        elif server.server_path:
            await client.connect(server.server_path)
        else:
            await client.connect_stdio(
                server.server_command,
                server.server_args or [],
                server.server_env or {}
            )
        
        # Discover capabilities
        await client.discover_capabilities()
        
        # Format capabilities
        capabilities = {
            "tools": [
                {
                    "name": tool.name,
                    "description": getattr(tool, 'description', ''),
                    "inputSchema": getattr(tool, 'inputSchema', {})
                }
                for tool in client.available_tools
            ],
            "resources": [
                {
                    "uri": str(resource.uri),
                    "name": getattr(resource, 'name', ''),
                    "description": getattr(resource, 'description', ''),
                    "mimeType": getattr(resource, 'mimeType', '')
                }
                for resource in client.available_resources
            ],
            "prompts": [
                {
                    "name": prompt.name,
                    "description": getattr(prompt, 'description', ''),
                    "arguments": getattr(prompt, 'arguments', [])
                }
                for prompt in client.available_prompts
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Update database
        db.update_server_capabilities(server_id, capabilities)
        
        return capabilities 