"""
Main CLI entry point for the MCP Client.

This module provides the command-line interface for connecting to and
interacting with MCP servers.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from .client import MCPClient, MCPClientConfig


# Load environment variables
load_dotenv()

console = Console()


@click.group(invoke_without_command=True)
@click.option('--server', '-s', help='Server script path or URL')
@click.option('--transport', '-t', 
              type=click.Choice(['stdio', 'sse', 'auto']), 
              default='auto',
              help='Transport type (stdio, sse, auto)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--timeout', default=30, help='Connection timeout in seconds')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx, server, transport, debug, timeout, config):
    """
    MCP Client - Connect to and interact with Model Context Protocol servers.
    
    Examples:
        # Connect to a Python server
        mcp-client -s server.py
        
        # Connect to a Node.js server  
        mcp-client -s server.js
        
        # Connect to an SSE server
        mcp-client -s http://localhost:8000/sse -t sse
        
        # Interactive mode (default)
        mcp-client -s server.py interactive
        
        # List server capabilities
        mcp-client -s server.py list
        
        # Call a specific tool
        mcp-client -s server.py tool my_tool arg1=value1 arg2=value2
    """
    ctx.ensure_object(dict)
    
    # Load configuration
    if config:
        ctx.obj['config'] = _load_config_file(config)
    else:
        ctx.obj['config'] = MCPClientConfig(
            transport_type=transport,
            timeout=timeout,
            debug=debug
        )
    
    ctx.obj['server'] = server
    
    # If no subcommand is specified, run interactive mode
    if ctx.invoked_subcommand is None:
        if not server:
            console.print("[red]Error: Server path or URL is required[/red]")
            console.print("Use --help for usage information.")
            sys.exit(1)
        ctx.invoke(interactive)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start an interactive session with the MCP server."""
    server = ctx.obj['server']
    config = ctx.obj['config']
    
    if not server:
        console.print("[red]Error: Server path or URL is required[/red]")
        sys.exit(1)
    
    asyncio.run(_run_interactive(server, config))


@cli.command()
@click.pass_context
def list(ctx):
    """List all capabilities (resources, tools, prompts) from the server."""
    server = ctx.obj['server']
    config = ctx.obj['config']
    
    if not server:
        console.print("[red]Error: Server path or URL is required[/red]")
        sys.exit(1)
    
    asyncio.run(_run_list_capabilities(server, config))


@cli.command()
@click.argument('tool_name')
@click.argument('args', nargs=-1)
@click.pass_context
def tool(ctx, tool_name, args):
    """
    Call a specific tool on the server.
    
    TOOL_NAME: Name of the tool to call
    ARGS: Tool arguments in key=value format
    
    Example: mcp-client -s server.py tool add a=5 b=3
    """
    server = ctx.obj['server']
    config = ctx.obj['config']
    
    if not server:
        console.print("[red]Error: Server path or URL is required[/red]")
        sys.exit(1)
    
    # Parse tool arguments
    tool_args = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Try to parse as JSON, fallback to string
            try:
                tool_args[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                tool_args[key] = value
        else:
            console.print(f"[yellow]Warning: Ignoring invalid argument: {arg}[/yellow]")
    
    asyncio.run(_run_tool_call(server, config, tool_name, tool_args))


@cli.command()
@click.argument('uri')
@click.pass_context
def resource(ctx, uri):
    """
    Read a resource from the server.
    
    URI: The resource URI to read
    
    Example: mcp-client -s server.py resource file:///path/to/file.txt
    """
    server = ctx.obj['server']
    config = ctx.obj['config']
    
    if not server:
        console.print("[red]Error: Server path or URL is required[/red]")
        sys.exit(1)
    
    asyncio.run(_run_resource_read(server, config, uri))


@cli.command()
@click.argument('prompt_name')
@click.argument('args', nargs=-1)
@click.pass_context
def prompt(ctx, prompt_name, args):
    """
    Get a prompt from the server.
    
    PROMPT_NAME: Name of the prompt to get
    ARGS: Prompt arguments in key=value format
    
    Example: mcp-client -s server.py prompt code_review code="print('hello')"
    """
    server = ctx.obj['server']
    config = ctx.obj['config']
    
    if not server:
        console.print("[red]Error: Server path or URL is required[/red]")
        sys.exit(1)
    
    # Parse prompt arguments
    prompt_args = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            prompt_args[key] = value
        else:
            console.print(f"[yellow]Warning: Ignoring invalid argument: {arg}[/yellow]")
    
    asyncio.run(_run_prompt_get(server, config, prompt_name, prompt_args))


@cli.command()
@click.argument('server_path')
@click.option('--output', '-o', type=click.Path(), help='Output file for capabilities')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'yaml', 'table']), 
              default='table',
              help='Output format')
def inspect(server_path, output, output_format):
    """
    Inspect a server and output its capabilities.
    
    SERVER_PATH: Path to the server script
    """
    config = MCPClientConfig()
    asyncio.run(_run_inspect(server_path, config, output, output_format))


@cli.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"MCP Client version: {__version__}")


async def _run_interactive(server: str, config: MCPClientConfig):
    """Run the interactive session."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server}[/blue]")
            await client.connect(server)
            
            console.print("[green]✅ Connected successfully![/green]")
            
            # Discover capabilities
            console.print("[blue]🔍 Discovering server capabilities...[/blue]")
            await client.discover_capabilities()
            
            # Show capabilities summary
            total_capabilities = (
                len(client.available_resources) + 
                len(client.available_tools) + 
                len(client.available_prompts)
            )
            console.print(f"[green]Found {total_capabilities} capabilities[/green]")
            
            # Start interactive session
            await client.interactive_session()
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


async def _run_list_capabilities(server: str, config: MCPClientConfig):
    """List server capabilities."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server}[/blue]")
            await client.connect(server)
            
            console.print("[blue]🔍 Discovering server capabilities...[/blue]")
            await client.discover_capabilities()
            
            client.display_capabilities()
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


async def _run_tool_call(server: str, config: MCPClientConfig, tool_name: str, tool_args: dict):
    """Call a specific tool."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server}[/blue]")
            await client.connect(server)
            
            console.print(f"[blue]🔧 Calling tool: {tool_name}[/blue]")
            result = await client.call_tool(tool_name, tool_args)
            
            console.print(f"[green]✅ Tool '{tool_name}' executed successfully:[/green]")
            
            # Display result
            if hasattr(result, 'content') and result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        console.print(Panel(content_item.text, title="Result"))
                    elif hasattr(content_item, 'data'):
                        console.print(Panel(str(content_item.data), title="Data"))
            else:
                console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


async def _run_resource_read(server: str, config: MCPClientConfig, uri: str):
    """Read a specific resource."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server}[/blue]")
            await client.connect(server)
            
            console.print(f"[blue]📖 Reading resource: {uri}[/blue]")
            result = await client.read_resource(uri)
            
            console.print(f"[green]✅ Resource '{uri}' read successfully:[/green]")
            
            # Display content
            if hasattr(result, 'contents') and result.contents:
                for content_item in result.contents:
                    if hasattr(content_item, 'text'):
                        console.print(Panel(content_item.text, title=f"Content ({getattr(content_item, 'mimeType', 'text')})"))
                    elif hasattr(content_item, 'data'):
                        console.print(Panel(f"Binary data ({len(content_item.data)} bytes)", title="Binary Content"))
            else:
                console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


async def _run_prompt_get(server: str, config: MCPClientConfig, prompt_name: str, prompt_args: dict):
    """Get a specific prompt."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server}[/blue]")
            await client.connect(server)
            
            console.print(f"[blue]💬 Getting prompt: {prompt_name}[/blue]")
            result = await client.get_prompt(prompt_name, prompt_args)
            
            console.print(f"[green]✅ Prompt '{prompt_name}' retrieved successfully:[/green]")
            
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
                        
                    console.print(Panel(
                        content_text,
                        title=f"Message {i+1} ({role})"
                    ))
            else:
                console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


async def _run_inspect(server_path: str, config: MCPClientConfig, output: Optional[str], output_format: str):
    """Inspect server capabilities and optionally save to file."""
    async with MCPClient(config) as client:
        try:
            console.print(f"[blue]🔄 Connecting to server: {server_path}[/blue]")
            await client.connect(server_path)
            
            console.print("[blue]🔍 Discovering server capabilities...[/blue]")
            await client.discover_capabilities()
            
            # Collect capabilities data
            capabilities_data = {
                'resources': [
                    {
                        'uri': r.uri,
                        'name': getattr(r, 'name', None),
                        'description': getattr(r, 'description', None),
                        'mimeType': getattr(r, 'mimeType', None)
                    } for r in client.available_resources
                ],
                'tools': [
                    {
                        'name': t.name,
                        'description': getattr(t, 'description', None),
                        'inputSchema': getattr(t, 'inputSchema', None)
                    } for t in client.available_tools
                ],
                'prompts': [
                    {
                        'name': p.name,
                        'description': getattr(p, 'description', None),
                        'arguments': getattr(p, 'arguments', None)
                    } for p in client.available_prompts
                ]
            }
            
            if output:
                # Save to file
                if output_format == 'json':
                    with open(output, 'w') as f:
                        json.dump(capabilities_data, f, indent=2, default=str)
                elif output_format == 'yaml':
                    import yaml
                    with open(output, 'w') as f:
                        yaml.dump(capabilities_data, f, default_flow_style=False)
                
                console.print(f"[green]✅ Capabilities saved to {output}[/green]")
            else:
                # Display to console
                if output_format == 'json':
                    console.print(json.dumps(capabilities_data, indent=2, default=str))
                else:
                    client.display_capabilities()
                    
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if config.debug:
                import traceback
                console.print(traceback.format_exc())
            sys.exit(1)


def _load_config_file(config_path: str) -> MCPClientConfig:
    """Load configuration from a file."""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    if path.suffix.lower() == '.json':
        with open(path) as f:
            config_data = json.load(f)
    elif path.suffix.lower() in ('.yaml', '.yml'):
        import yaml
        with open(path) as f:
            config_data = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {path.suffix}")
    
    return MCPClientConfig(**config_data)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]💥 Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main() 