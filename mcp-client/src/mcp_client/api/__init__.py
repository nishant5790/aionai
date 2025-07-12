"""
API module for MCP Client.

This module provides REST API endpoints for managing MCP servers,
executing queries, and running intelligent conversations.
"""

from .app import create_app
from .routes import servers, queries, chat, health

__all__ = ["create_app"] 