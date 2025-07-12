"""
Database models for MCP Client.

This module defines SQLAlchemy models for storing MCP server configurations,
query history, and user data.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import json
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, JSON, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from pydantic import BaseModel, ConfigDict

Base = declarative_base()


class User(Base):
    """User model for authentication and session management."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    mcp_servers = relationship("MCPServer", back_populates="owner")
    query_history = relationship("QueryHistory", back_populates="user")


class MCPServer(Base):
    """Model for storing MCP server configurations."""
    
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Server connection details
    server_type = Column(String(20), nullable=False)  # stdio, sse, streamable_http
    server_path = Column(String(500), nullable=True)  # For local servers
    server_url = Column(String(500), nullable=True)   # For remote servers
    server_command = Column(String(200), nullable=True)
    server_args = Column(JSON, nullable=True)
    server_env = Column(JSON, nullable=True)
    
    # Server metadata
    capabilities = Column(JSON, nullable=True)
    last_ping = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="mcp_servers")
    query_history = relationship("QueryHistory", back_populates="mcp_server")


class QueryHistory(Base):
    """Model for storing query history and results."""
    
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(20), nullable=False)  # tool, resource, prompt, chat
    
    # Query details
    tool_name = Column(String(100), nullable=True)
    tool_args = Column(JSON, nullable=True)
    resource_uri = Column(String(500), nullable=True)
    prompt_name = Column(String(100), nullable=True)
    prompt_args = Column(JSON, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Integer, nullable=True)  # milliseconds
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mcp_server_id = Column(Integer, ForeignKey("mcp_servers.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="query_history")
    mcp_server = relationship("MCPServer", back_populates="query_history")


# Pydantic models for API
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class MCPServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    server_type: str
    server_path: Optional[str] = None
    server_url: Optional[str] = None
    server_command: Optional[str] = None
    server_args: Optional[List[str]] = None
    server_env: Optional[Dict[str, Any]] = None


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    server_type: Optional[str] = None
    server_path: Optional[str] = None
    server_url: Optional[str] = None
    server_command: Optional[str] = None
    server_args: Optional[List[str]] = None
    server_env: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MCPServerResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    server_type: str
    server_path: Optional[str]
    server_url: Optional[str]
    server_command: Optional[str]
    server_args: Optional[List[str]]
    server_env: Optional[Dict[str, Any]]
    capabilities: Optional[Dict[str, Any]]
    last_ping: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    owner_id: int
    
    model_config = ConfigDict(from_attributes=True)


class QueryRequest(BaseModel):
    query_text: str
    query_type: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    resource_uri: Optional[str] = None
    prompt_name: Optional[str] = None
    prompt_args: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    id: int
    query_text: str
    query_type: str
    tool_name: Optional[str]
    tool_args: Optional[Dict[str, Any]]
    resource_uri: Optional[str]
    prompt_name: Optional[str]
    prompt_args: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_time: Optional[int]
    created_at: datetime
    user_id: int
    mcp_server_id: int
    
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    mcp_server_id: int
    llm_provider: str = "openai"  # openai, anthropic, bedrock
    model_name: str = "gpt-4o"
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[list] = None
    execution_time: int
    tokens_used: Optional[int] = None 