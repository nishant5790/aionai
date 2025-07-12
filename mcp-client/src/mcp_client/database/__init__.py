"""
Database module for MCP Client.

This module provides database models and operations for storing
MCP server configurations, query history, and user data.
"""

from .models import MCPServer, QueryHistory, User
from .database import Database

__all__ = ["MCPServer", "QueryHistory", "User", "Database"] 