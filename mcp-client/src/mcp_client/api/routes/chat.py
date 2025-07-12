"""
Chat endpoints for LLM-powered conversations with MCP tools.

This module provides endpoints for intelligent conversations
that can automatically use MCP tools based on user input.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status

from ...database.database import get_database
from ...database.models import ChatRequest, MCPServer, User
from ...llm.agent import get_agent_manager, create_mcp_agent
from .servers import get_current_user

router = APIRouter()


@router.post("/{server_id}")
async def chat_with_server(
    server_id: int,
    request: ChatRequest,
    user: User = Depends(get_current_user)
):
    """Start a chat conversation with an MCP server using LLM."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    try:
        agent_manager = get_agent_manager()
        
        # Get or create agent for this server
        agent = agent_manager.get_agent(server_id)
        
        if not agent:
            # Create new agent
            server_config = {
                "server_command": server.server_command,
                "server_args": server.server_args or [],
                "server_env": server.server_env or {},
                "server_type": server.server_type,
                "server_path": server.server_path,
                "server_url": server.server_url
            }
            
            llm_config = {
                "provider": request.llm_provider,
                "kwargs": {}
            }
            
            agent = await agent_manager.create_agent(
                server_id, 
                server_config, 
                llm_config, 
                request.system_prompt
            )
        
        # Process chat message
        response = await agent.chat(
            message=request.message,
            model=request.model_name,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Log the conversation
        query_data = {
            "query_text": request.message,
            "query_type": "chat",
            "result": {
                "response": response["response"],
                "tool_calls": response.get("tool_calls", []),
                "tokens_used": response.get("tokens_used", 0)
            },
            "execution_time": response.get("execution_time", 0)
        }
        
        db.log_query(user.id, server_id, query_data)
        
        return {
            "response": response["response"],
            "tool_calls": response.get("tool_calls", []),
            "execution_time": response.get("execution_time", 0),
            "tokens_used": response.get("tokens_used", 0),
            "iterations": response.get("iterations", 1),
            "timestamp": response.get("timestamp", datetime.utcnow().isoformat())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/{server_id}/reset")
async def reset_conversation(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Reset the conversation history for a server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    agent_manager = get_agent_manager()
    agent = agent_manager.get_agent(server_id)
    
    if agent:
        await agent.reset_conversation()
        return {"message": "Conversation reset successfully"}
    else:
        return {"message": "No active conversation found"}


@router.get("/{server_id}/history")
async def get_conversation_history(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Get the conversation history for a server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    agent_manager = get_agent_manager()
    agent = agent_manager.get_agent(server_id)
    
    if agent:
        history = agent.get_conversation_history()
        return {
            "conversation_history": history,
            "message_count": len(history)
        }
    else:
        return {
            "conversation_history": [],
            "message_count": 0
        }


@router.get("/{server_id}/tools")
async def get_available_tools(
    server_id: int,
    user: User = Depends(get_current_user)
):
    """Get information about available tools for a server."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    agent_manager = get_agent_manager()
    agent = agent_manager.get_agent(server_id)
    
    if agent:
        tool_info = await agent.get_tool_info()
        return tool_info
    else:
        # Create temporary agent to get tool info
        try:
            server_config = {
                "server_command": server.server_command,
                "server_args": server.server_args or [],
                "server_env": server.server_env or {},
                "server_type": server.server_type,
                "server_path": server.server_path,
                "server_url": server.server_url
            }
            
            llm_config = {
                "provider": "openai",
                "kwargs": {}
            }
            
            agent = await create_mcp_agent(server_config, llm_config)
            tool_info = await agent.get_tool_info()
            
            # Close the temporary agent
            await agent.tool_manager.mcp_client.close()
            
            return tool_info
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get tool info: {str(e)}"
            )


@router.post("/{server_id}/tool/{tool_name}")
async def execute_tool_directly(
    server_id: int,
    tool_name: str,
    tool_args: dict,
    user: User = Depends(get_current_user)
):
    """Execute a tool directly without LLM interaction."""
    db = get_database()
    server = db.get_server_by_id(server_id)
    
    if not server or server.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    try:
        agent_manager = get_agent_manager()
        agent = agent_manager.get_agent(server_id)
        
        if not agent:
            # Create temporary agent
            server_config = {
                "server_command": server.server_command,
                "server_args": server.server_args or [],
                "server_env": server.server_env or {},
                "server_type": server.server_type,
                "server_path": server.server_path,
                "server_url": server.server_url
            }
            
            llm_config = {
                "provider": "openai",
                "kwargs": {}
            }
            
            agent = await create_mcp_agent(server_config, llm_config)
            temporary_agent = True
        else:
            temporary_agent = False
        
        # Execute tool
        result = await agent.execute_tool_directly(tool_name, tool_args)
        
        # Close temporary agent
        if temporary_agent:
            await agent.tool_manager.mcp_client.close()
        
        # Log the execution
        query_data = {
            "query_text": f"Direct tool: {tool_name}",
            "query_type": "tool",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "result": result,
            "execution_time": result.get("execution_time_ms", 0)
        }
        
        db.log_query(user.id, server_id, query_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.get("/providers")
async def get_llm_providers():
    """Get available LLM providers and their models."""
    return {
        "providers": {
            "openai": {
                "name": "OpenAI",
                "models": [
                    "gpt-4o",
                    "gpt-4o-mini", 
                    "gpt-4-turbo",
                    "gpt-3.5-turbo"
                ],
                "supports_tools": True,
                "required_env": ["OPENAI_API_KEY"]
            },
            "anthropic": {
                "name": "Anthropic",
                "models": [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-haiku-20240307",
                    "claude-3-opus-20240229"
                ],
                "supports_tools": True,
                "required_env": ["ANTHROPIC_API_KEY"]
            },
            "bedrock": {
                "name": "AWS Bedrock",
                "models": [
                    "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "anthropic.claude-3-haiku-20240307-v1:0",
                    "anthropic.claude-3-opus-20240229-v1:0"
                ],
                "supports_tools": True,
                "required_env": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
            }
        },
        "default_provider": "openai",
        "default_model": "gpt-4o"
    } 