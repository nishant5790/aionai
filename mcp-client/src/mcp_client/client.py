"""
Main MCP Client implementation.

This module provides the MCPClient class which can connect to any MCP server
using various transport mechanisms (stdio, SSE, streamable HTTP).
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListToolsResult,
    Prompt,
    ReadResourceResult,
    Resource,
    Tool,
)
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class MCPClientConfig(BaseModel):
    """Configuration for MCP Client."""
    
    server_command: Optional[str] = None
    server_args: List[str] = []
    server_env: Dict[str, str] = {}
    transport_type: str = "stdio"  # stdio, sse, streamable_http
    server_url: Optional[str] = None
    timeout: int = 30
    debug: bool = False


class MCPClient:
    """
    A comprehensive MCP client that can connect to any MCP server.
    
    This client supports multiple transport mechanisms:
    - stdio: Communication via standard input/output (for local servers)
    - SSE: Server-Sent Events over HTTP
    - streamable_http: HTTP-based streaming transport
    """
    
    def __init__(self, config: Optional[MCPClientConfig] = None):
        """
        Initialize the MCP client.
        
        Args:
            config: Configuration object for the client
        """
        self.config = config or MCPClientConfig()
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.console = Console()
        self.logger = self._setup_logging()
        
        # Server capabilities
        self.available_resources: List[Resource] = []
        self.available_tools: List[Tool] = []
        self.available_prompts: List[Prompt] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the client."""
        logger = logging.getLogger("mcp_client")
        if self.config.debug:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
        
    async def connect_stdio(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> None:
        """
        Connect to an MCP server using stdio transport.
        
        Args:
            command: The command to run the server
            args: Arguments to pass to the server
            env: Environment variables for the server
        """
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {}
        )
        
        self.logger.debug(f"Connecting to stdio server: {command} {' '.join(args)}")
        
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            self.logger.info("Successfully connected via stdio")
            
        except Exception as e:
            self.logger.error(f"Failed to connect via stdio: {e}")
            raise
            
    async def connect_sse(self, url: str) -> None:
        """
        Connect to an MCP server using SSE transport.
        
        Args:
            url: The SSE endpoint URL
        """
        self.logger.debug(f"Connecting to SSE server: {url}")
        
        try:
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(url)
            )
            read_stream, write_stream = sse_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            self.logger.info("Successfully connected via SSE")
            
        except Exception as e:
            self.logger.error(f"Failed to connect via SSE: {e}")
            raise
            
    async def connect(self, 
                     server_path_or_url: Optional[str] = None,
                     transport: Optional[str] = None) -> None:
        """
        Connect to an MCP server using the specified or auto-detected transport.
        
        Args:
            server_path_or_url: Path to server script or URL
            transport: Transport type (stdio, sse, streamable_http)
        """
        transport = transport or self.config.transport_type
        
        if server_path_or_url:
            # Auto-detect transport type if not specified
            if transport == "auto":
                if server_path_or_url.startswith(("http://", "https://")):
                    transport = "sse"
                else:
                    transport = "stdio"
                    
            if transport == "stdio":
                await self._connect_stdio_auto(server_path_or_url)
            elif transport == "sse":
                await self.connect_sse(server_path_or_url)
            else:
                raise ValueError(f"Unsupported transport type: {transport}")
        elif self.config.server_command:
            await self.connect_stdio(
                self.config.server_command,
                self.config.server_args,
                self.config.server_env
            )
        else:
            raise ValueError("No server specified. Provide server_path_or_url or configure server_command")
            
    async def _connect_stdio_auto(self, server_path: str) -> None:
        """Auto-detect and connect to a stdio server based on file extension."""
        path = Path(server_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Server file not found: {server_path}")
            
        # Determine command based on file extension
        extension = path.suffix.lower()
        
        if extension == ".py":
            command = sys.executable
        elif extension == ".js":
            command = "node"
        elif extension == ".ts":
            # Assume ts-node is available
            command = "npx"
            server_path = f"ts-node {server_path}"
        else:
            # Try to make it executable and run directly
            command = str(path.absolute())
            server_path = ""
            
        args = [server_path] if server_path else []
        await self.connect_stdio(command, args)
        
    async def discover_capabilities(self) -> None:
        """Discover and cache server capabilities."""
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        try:
            # List resources
            try:
                resources_result = await self.session.list_resources()
                self.available_resources = resources_result.resources
                self.logger.debug(f"Found {len(self.available_resources)} resources")
            except Exception as e:
                self.logger.warning(f"Failed to list resources: {e}")
                self.available_resources = []
                
            # List tools
            try:
                tools_result = await self.session.list_tools()
                self.available_tools = tools_result.tools
                self.logger.debug(f"Found {len(self.available_tools)} tools")
            except Exception as e:
                self.logger.warning(f"Failed to list tools: {e}")
                self.available_tools = []
                
            # List prompts
            try:
                prompts_result = await self.session.list_prompts()
                self.available_prompts = prompts_result.prompts
                self.logger.debug(f"Found {len(self.available_prompts)} prompts")
            except Exception as e:
                self.logger.warning(f"Failed to list prompts: {e}")
                self.available_prompts = []
                
        except Exception as e:
            self.logger.error(f"Failed to discover capabilities: {e}")
            raise
            
    def display_capabilities(self) -> None:
        """Display server capabilities in a formatted table."""
        self.console.print("\n[bold blue]🔍 Server Capabilities[/bold blue]")
        
        # Resources table
        if self.available_resources:
            resources_table = Table(title="📚 Resources")
            resources_table.add_column("URI", style="cyan")
            resources_table.add_column("Name", style="green")
            resources_table.add_column("Description", style="white")
            resources_table.add_column("MIME Type", style="yellow")
            
            for resource in self.available_resources:
                # Convert URI to string to handle AnyUrl objects
                uri_str = str(resource.uri) if hasattr(resource, 'uri') else 'N/A'
                resources_table.add_row(
                    uri_str,
                    getattr(resource, 'name', 'N/A'),
                    getattr(resource, 'description', 'N/A'),
                    getattr(resource, 'mimeType', 'N/A')
                )
            self.console.print(resources_table)
            
        # Tools table
        if self.available_tools:
            tools_table = Table(title="🛠️  Tools")
            tools_table.add_column("Name", style="cyan")
            tools_table.add_column("Description", style="white")
            tools_table.add_column("Input Schema", style="yellow")
            
            for tool in self.available_tools:
                schema_str = json.dumps(tool.inputSchema, indent=2) if hasattr(tool, 'inputSchema') else 'N/A'
                tools_table.add_row(
                    tool.name,
                    getattr(tool, 'description', 'N/A'),
                    schema_str[:100] + "..." if len(schema_str) > 100 else schema_str
                )
            self.console.print(tools_table)
            
        # Prompts table
        if self.available_prompts:
            prompts_table = Table(title="💬 Prompts")
            prompts_table.add_column("Name", style="cyan")
            prompts_table.add_column("Description", style="white")
            prompts_table.add_column("Arguments", style="yellow")
            
            for prompt in self.available_prompts:
                args_str = str(getattr(prompt, 'arguments', [])) if hasattr(prompt, 'arguments') else 'N/A'
                prompts_table.add_row(
                    prompt.name,
                    getattr(prompt, 'description', 'N/A'),
                    args_str
                )
            self.console.print(prompts_table)
            
        if not (self.available_resources or self.available_tools or self.available_prompts):
            self.console.print("[yellow]No capabilities found or server doesn't expose any.[/yellow]")
            
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        Call a tool on the server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            The result of the tool call
        """
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        self.logger.debug(f"Calling tool: {tool_name} with args: {arguments}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            self.logger.debug(f"Tool call result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            raise
            
    async def read_resource(self, uri: str) -> ReadResourceResult:
        """
        Read a resource from the server.
        
        Args:
            uri: URI of the resource to read
            
        Returns:
            The resource content and metadata
        """
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        self.logger.debug(f"Reading resource: {uri}")
        
        try:
            result = await self.session.read_resource(uri)
            self.logger.debug(f"Resource read result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Resource read failed: {e}")
            raise
            
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:
        """
        Get a prompt from the server.
        
        Args:
            prompt_name: Name of the prompt to get
            arguments: Arguments to pass to the prompt
            
        Returns:
            The prompt result
        """
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        self.logger.debug(f"Getting prompt: {prompt_name} with args: {arguments}")
        
        try:
            result = await self.session.get_prompt(prompt_name, arguments or {})
            self.logger.debug(f"Prompt result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Get prompt failed: {e}")
            raise
            
    async def interactive_session(self) -> None:
        """Run an interactive session with the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        self.console.print(Panel.fit(
            "[bold green]🚀 MCP Interactive Session Started![/bold green]\n"
            "Available commands:\n"
            "  • [cyan]list[/cyan] - Show available capabilities\n"
            "  • [cyan]tool <name> [args...][/cyan] - Call a tool\n"
            "  • [cyan]resource <uri>[/cyan] - Read a resource\n"
            "  • [cyan]prompt <name> [args...][/cyan] - Get a prompt\n"
            "  • [cyan]help[/cyan] - Show this help\n"
            "  • [cyan]quit[/cyan] - Exit session",
            title="MCP Client"
        ))
        
        while True:
            try:
                command = self.console.input("\n[bold cyan]mcp>[/bold cyan] ").strip()
                
                if not command:
                    continue
                    
                parts = command.split()
                cmd = parts[0].lower()
                
                if cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "help":
                    self._show_help()
                elif cmd == "list":
                    self.display_capabilities()
                elif cmd == "tool":
                    await self._handle_tool_command(parts[1:])
                elif cmd == "resource":
                    await self._handle_resource_command(parts[1:])
                elif cmd == "prompt":
                    await self._handle_prompt_command(parts[1:])
                else:
                    self.console.print(f"[red]Unknown command: {cmd}[/red]")
                    self.console.print("Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'quit' to exit.[/yellow]")
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                
        self.console.print("[yellow]👋 Goodbye![/yellow]")
        
    def _show_help(self) -> None:
        """Show detailed help information."""
        help_text = """
[bold]MCP Client Commands:[/bold]

[cyan]list[/cyan]
    Show all available resources, tools, and prompts from the server

[cyan]tool <name> [key=value...][/cyan]
    Call a tool with optional arguments
    Example: tool add a=5 b=3

[cyan]resource <uri>[/cyan]
    Read a resource by its URI
    Example: resource file:///path/to/file.txt

[cyan]prompt <name> [key=value...][/cyan]
    Get a prompt with optional arguments
    Example: prompt code_review code="print('hello')"

[cyan]help[/cyan]
    Show this help message

[cyan]quit[/cyan]
    Exit the interactive session
        """
        self.console.print(Panel(help_text, title="Help"))
        
    async def _handle_tool_command(self, args: List[str]) -> None:
        """Handle tool command execution."""
        if not args:
            self.console.print("[red]Error: Tool name required[/red]")
            return
            
        tool_name = args[0]
        
        # Parse arguments (key=value format)
        tool_args = {}
        for arg in args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                # Try to parse as JSON, fallback to string
                try:
                    tool_args[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    tool_args[key] = value
            else:
                self.console.print(f"[yellow]Warning: Ignoring invalid argument: {arg}[/yellow]")
                
        try:
            result = await self.call_tool(tool_name, tool_args)
            self.console.print(f"[green]✅ Tool '{tool_name}' executed successfully:[/green]")
            
            # Display result in a nice format
            if hasattr(result, 'content') and result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        self.console.print(Panel(content_item.text, title="Result"))
                    elif hasattr(content_item, 'data'):
                        self.console.print(Panel(str(content_item.data), title="Data"))
            else:
                self.console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            self.console.print(f"[red]❌ Tool execution failed: {e}[/red]")
            
    async def _handle_resource_command(self, args: List[str]) -> None:
        """Handle resource command execution."""
        if not args:
            self.console.print("[red]Error: Resource URI required[/red]")
            return
            
        uri = args[0]
        
        try:
            result = await self.read_resource(uri)
            self.console.print(f"[green]✅ Resource '{uri}' read successfully:[/green]")
            
            # Display content
            if hasattr(result, 'contents') and result.contents:
                for content_item in result.contents:
                    if hasattr(content_item, 'text'):
                        # Syntax highlight if it looks like code
                        if uri.endswith(('.py', '.js', '.json', '.yaml', '.yml', '.xml', '.html')):
                            ext = uri.split('.')[-1]
                            syntax = Syntax(content_item.text, ext, theme="monokai", line_numbers=True)
                            self.console.print(Panel(syntax, title=f"Content ({getattr(content_item, 'mimeType', 'text')})"))
                        else:
                            self.console.print(Panel(content_item.text, title=f"Content ({getattr(content_item, 'mimeType', 'text')})"))
                    elif hasattr(content_item, 'data'):
                        self.console.print(Panel(f"Binary data ({len(content_item.data)} bytes)", title="Binary Content"))
            else:
                self.console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            self.console.print(f"[red]❌ Resource read failed: {e}[/red]")
            
    async def _handle_prompt_command(self, args: List[str]) -> None:
        """Handle prompt command execution."""
        if not args:
            self.console.print("[red]Error: Prompt name required[/red]")
            return
            
        prompt_name = args[0]
        
        # Parse arguments (key=value format)
        prompt_args = {}
        for arg in args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                prompt_args[key] = value
            else:
                self.console.print(f"[yellow]Warning: Ignoring invalid argument: {arg}[/yellow]")
                
        try:
            result = await self.get_prompt(prompt_name, prompt_args)
            self.console.print(f"[green]✅ Prompt '{prompt_name}' retrieved successfully:[/green]")
            
            # Display prompt messages
            if hasattr(result, 'messages') and result.messages:
                for i, message in enumerate(result.messages):
                    role = getattr(message, 'role', 'unknown')
                    content = getattr(message, 'content', '')
                    
                    if hasattr(content, 'text'):
                        content_text = content.text
                    elif isinstance(content, str):
                        content_text = content
                    else:
                        content_text = str(content)
                        
                    self.console.print(Panel(
                        content_text,
                        title=f"Message {i+1} ({role})"
                    ))
            else:
                self.console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            self.console.print(f"[red]❌ Prompt retrieval failed: {e}[/red]")
            
    async def close(self) -> None:
        """Close the client and clean up resources."""
        await self.exit_stack.aclose()
        self.logger.info("MCP Client closed")
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close() 