"""
MCP Client - A comprehensive Python client for Model Context Protocol servers.

This package provides tools to connect to and interact with any MCP server,
supporting multiple transport mechanisms and providing rich CLI interfaces.
"""

__version__ = "0.1.0"
__author__ = "MCP Client Team"
__description__ = "A comprehensive Python MCP client that can connect to any MCP server"

from .client import MCPClient, MCPClientConfig
from .main import main

__all__ = ["MCPClient", "MCPClientConfig", "main"] 