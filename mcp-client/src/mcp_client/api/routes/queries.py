"""
Query execution endpoints for MCP operations.

This module provides endpoints for executing MCP tools,
reading resources, and getting prompts.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from ...database.database import get_database
from ...database.models import (
    QueryRequest, QueryResponse, MCPServer, User
)
from ...client import MCPClient, MCPClientConfig
from .servers import get_current_user

router = APIRouter()


@router.post("/{server_id}/tool")
async def execute_tool(
    server_id: int,
    tool_name: str,
    tool_args: dict,
    user: User = Depends(get_current_user)
):
    """Execute a tool on an MCP server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Create MCP client and execute tool
        config = MCPClientConfig(
            server_command=server.server_command,
            server_args=server.server_args or [],
            server_env=server.server_env or {},
            transport_type=server.server_type,
            timeout=30,
            debug=False
        )
        
        async with MCPClient(config) as client:
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
            
            result = await client.call_tool(tool_name, tool_args)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Format result
            formatted_result = []
            if hasattr(result, 'content') and result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        formatted_result.append(content_item.text)
                    else:
                        formatted_result.append(str(content_item))
            
            # Log query
            query_data = {
                "query_text": f"Tool: {tool_name}",
                "query_type": "tool",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "result": {"content": formatted_result},
                "execution_time": int(execution_time)
            }
            
            db.log_query(user.id, server_id, query_data)
            
            return {
                "success": True,
                "tool_name": tool_name,
                "arguments": tool_args,
                "result": formatted_result,
                "execution_time_ms": int(execution_time),
                "timestamp": start_time.isoformat()
            }
            
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log error
        query_data = {
            "query_text": f"Tool: {tool_name}",
            "query_type": "tool",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "error_message": str(e),
            "execution_time": int(execution_time)
        }
        
        db.log_query(user.id, server_id, query_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.get("/{server_id}/resource")
async def read_resource(
    server_id: int,
    resource_uri: str,
    user: User = Depends(get_current_user)
):
    """Read a resource from an MCP server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Create MCP client and read resource
        config = MCPClientConfig(
            server_command=server.server_command,
            server_args=server.server_args or [],
            server_env=server.server_env or {},
            transport_type=server.server_type,
            timeout=30,
            debug=False
        )
        
        async with MCPClient(config) as client:
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
            
            result = await client.read_resource(resource_uri)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Format result
            formatted_content = []
            if hasattr(result, 'contents') and result.contents:
                for content_item in result.contents:
                    if hasattr(content_item, 'text'):
                        formatted_content.append({
                            "type": "text",
                            "content": content_item.text,
                            "mimeType": getattr(content_item, 'mimeType', 'text/plain')
                        })
                    elif hasattr(content_item, 'data'):
                        formatted_content.append({
                            "type": "binary",
                            "size": len(content_item.data),
                            "mimeType": getattr(content_item, 'mimeType', 'application/octet-stream')
                        })
            
            # Log query
            query_data = {
                "query_text": f"Resource: {resource_uri}",
                "query_type": "resource",
                "resource_uri": resource_uri,
                "result": {"content": formatted_content},
                "execution_time": int(execution_time)
            }
            
            db.log_query(user.id, server_id, query_data)
            
            return {
                "success": True,
                "resource_uri": resource_uri,
                "content": formatted_content,
                "execution_time_ms": int(execution_time),
                "timestamp": start_time.isoformat()
            }
            
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log error
        query_data = {
            "query_text": f"Resource: {resource_uri}",
            "query_type": "resource",
            "resource_uri": resource_uri,
            "error_message": str(e),
            "execution_time": int(execution_time)
        }
        
        db.log_query(user.id, server_id, query_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resource read failed: {str(e)}"
        )


@router.post("/{server_id}/prompt")
async def get_prompt(
    server_id: int,
    prompt_name: str,
    prompt_args: dict = {},
    user: User = Depends(get_current_user)
):
    """Get a prompt from an MCP server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Create MCP client and get prompt
        config = MCPClientConfig(
            server_command=server.server_command,
            server_args=server.server_args or [],
            server_env=server.server_env or {},
            transport_type=server.server_type,
            timeout=30,
            debug=False
        )
        
        async with MCPClient(config) as client:
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
            
            result = await client.get_prompt(prompt_name, prompt_args)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Format result
            formatted_messages = []
            if hasattr(result, 'messages') and result.messages:
                for message in result.messages:
                    formatted_messages.append({
                        "role": getattr(message, 'role', 'unknown'),
                        "content": getattr(message, 'content', {})
                    })
            
            # Log query
            query_data = {
                "query_text": f"Prompt: {prompt_name}",
                "query_type": "prompt",
                "prompt_name": prompt_name,
                "prompt_args": prompt_args,
                "result": {"messages": formatted_messages},
                "execution_time": int(execution_time)
            }
            
            db.log_query(user.id, server_id, query_data)
            
            return {
                "success": True,
                "prompt_name": prompt_name,
                "arguments": prompt_args,
                "messages": formatted_messages,
                "execution_time_ms": int(execution_time),
                "timestamp": start_time.isoformat()
            }
            
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log error
        query_data = {
            "query_text": f"Prompt: {prompt_name}",
            "query_type": "prompt",
            "prompt_name": prompt_name,
            "prompt_args": prompt_args,
            "error_message": str(e),
            "execution_time": int(execution_time)
        }
        
        db.log_query(user.id, server_id, query_data)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt retrieval failed: {str(e)}"
        )


@router.get("/history")
async def get_query_history(
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get query history for the current user."""
    db = get_database()
    history = db.get_query_history(user.id, limit)
    
    return [
        {
            "id": query.id,
            "query_text": query.query_text,
            "query_type": query.query_type,
            "result": query.result,
            "error_message": query.error_message,
            "execution_time": query.execution_time,
            "created_at": query.created_at.isoformat(),
            "server_id": query.mcp_server_id
        }
        for query in history
    ] 