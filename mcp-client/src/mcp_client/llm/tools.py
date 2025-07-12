"""
Tool management for MCP Client LLM integration.

This module handles the conversion of MCP tools into formats
that different LLM providers can understand and execute.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..client import MCPClient, MCPClientConfig


class ToolManager:
    """Manages MCP tools for LLM integration."""
    
    def __init__(self, mcp_client: MCPClient):
        """
        Initialize tool manager.
        
        Args:
            mcp_client: Connected MCP client instance
        """
        self.mcp_client = mcp_client
        self.available_tools = []
        self.tool_schemas = {}
    
    async def refresh_tools(self):
        """Refresh available tools from the MCP server."""
        if not self.mcp_client.session:
            raise RuntimeError("MCP client is not connected")
        
        await self.mcp_client.discover_capabilities()
        
        # Convert MCP tools to standardized format
        self.available_tools = []
        self.tool_schemas = {}
        
        for tool in self.mcp_client.available_tools:
            tool_dict = {
                "name": tool.name,
                "description": getattr(tool, 'description', ''),
                "inputSchema": getattr(tool, 'inputSchema', {})
            }
            
            self.available_tools.append(tool_dict)
            self.tool_schemas[tool.name] = tool_dict
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tools formatted for LLM consumption."""
        return self.available_tools.copy()
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        return self.tool_schemas.get(tool_name)
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Dictionary containing execution result
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate tool exists
            if tool_name not in self.tool_schemas:
                raise ValueError(f"Tool '{tool_name}' not found")
            
            # Execute the tool via MCP client
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Format result
            formatted_result = {
                "success": True,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": self._format_tool_result(result),
                "execution_time_ms": int(execution_time),
                "timestamp": start_time.isoformat()
            }
            
            return formatted_result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "success": False,
                "tool_name": tool_name,
                "arguments": arguments,
                "error": str(e),
                "execution_time_ms": int(execution_time),
                "timestamp": start_time.isoformat()
            }
    
    def _format_tool_result(self, mcp_result) -> Any:
        """Format MCP tool result for LLM consumption."""
        if hasattr(mcp_result, 'content') and mcp_result.content:
            # Extract text content from MCP result
            content_parts = []
            for content_item in mcp_result.content:
                if hasattr(content_item, 'text'):
                    content_parts.append(content_item.text)
                elif hasattr(content_item, 'data'):
                    content_parts.append(f"Binary data ({len(content_item.data)} bytes)")
                else:
                    content_parts.append(str(content_item))
            
            return "\n".join(content_parts) if content_parts else str(mcp_result)
        else:
            return str(mcp_result)
    
    async def execute_multiple_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple tools concurrently.
        
        Args:
            tool_calls: List of tool calls with 'name' and 'arguments'
            
        Returns:
            List of execution results
        """
        tasks = []
        for tool_call in tool_calls:
            task = self.execute_tool(
                tool_call.get("name"),
                tool_call.get("arguments", {})
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "success": False,
                    "tool_name": tool_calls[i].get("name", "unknown"),
                    "arguments": tool_calls[i].get("arguments", {}),
                    "error": str(result),
                    "execution_time_ms": 0,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                formatted_results.append(result)
        
        return formatted_results
    
    def get_tool_summary(self) -> Dict[str, Any]:
        """Get a summary of available tools."""
        return {
            "total_tools": len(self.available_tools),
            "tool_names": [tool["name"] for tool in self.available_tools],
            "tools_by_category": self._categorize_tools(),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _categorize_tools(self) -> Dict[str, List[str]]:
        """Categorize tools based on their names and descriptions."""
        categories = {
            "calculation": [],
            "data": [],
            "communication": [],
            "file": [],
            "utility": [],
            "other": []
        }
        
        for tool in self.available_tools:
            name = tool["name"].lower()
            description = tool.get("description", "").lower()
            
            if any(word in name or word in description for word in ["add", "multiply", "divide", "calculate", "math"]):
                categories["calculation"].append(tool["name"])
            elif any(word in name or word in description for word in ["read", "write", "data", "query", "search"]):
                categories["data"].append(tool["name"])
            elif any(word in name or word in description for word in ["send", "email", "message", "notify"]):
                categories["communication"].append(tool["name"])
            elif any(word in name or word in description for word in ["file", "download", "upload", "save"]):
                categories["file"].append(tool["name"])
            elif any(word in name or word in description for word in ["time", "date", "echo", "status", "health"]):
                categories["utility"].append(tool["name"])
            else:
                categories["other"].append(tool["name"])
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}


async def create_tool_manager(server_config: Dict[str, Any]) -> ToolManager:
    """
    Create and initialize a tool manager for an MCP server.
    
    Args:
        server_config: Server configuration dictionary
        
    Returns:
        Initialized ToolManager instance
    """
    # Create MCP client configuration
    config = MCPClientConfig(
        server_command=server_config.get("server_command"),
        server_args=server_config.get("server_args", []),
        server_env=server_config.get("server_env", {}),
        transport_type=server_config.get("server_type", "stdio"),
        timeout=30,
        debug=False
    )
    
    # Create and connect MCP client
    client = MCPClient(config)
    
    # Determine connection method
    if server_config.get("server_url"):
        await client.connect(server_config["server_url"], server_config.get("server_type"))
    elif server_config.get("server_path"):
        await client.connect(server_config["server_path"])
    else:
        # Use command and args
        await client.connect_stdio(
            server_config["server_command"],
            server_config.get("server_args", []),
            server_config.get("server_env", {})
        )
    
    # Create tool manager and refresh tools
    tool_manager = ToolManager(client)
    await tool_manager.refresh_tools()
    
    return tool_manager 