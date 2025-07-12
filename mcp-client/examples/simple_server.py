#!/usr/bin/env python3
"""
Simple Example MCP Server

This is a basic MCP server implementation that demonstrates:
- Tools (calculator functions)
- Resources (configuration and status)
- Prompts (code review template)

Use this server to test the MCP client functionality.
"""

from mcp.server.fastmcp import FastMCP
import json
import os
from datetime import datetime


# Create the server
mcp = FastMCP("Simple Example Server")


# Tools
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers (a / b)."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent."""
    return base ** exponent


@mcp.tool()
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().isoformat()


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"

@mcp.tool()
def download_file(file_name , folder_name , data) -> str:
    """Download a file from the given URL."""
    file_path = os.path.join(folder_name, file_name)
    with open(file_path, 'w') as file:
        file.write(data)
    return f"File downloaded to {file_path}"


# Resources
@mcp.resource("config://server")
def get_server_config() -> str:
    """Get the server configuration."""
    config = {
        "server_name": "Simple Example Server",
        "version": "1.0.0",
        "features": ["calculator", "time", "echo"],
        "uptime": "Running since startup"
    }
    return json.dumps(config, indent=2)


@mcp.resource("status://health")
def get_server_status() -> str:
    """Get the server health status."""
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_available": 6,
        "resources_available": 3,
        "prompts_available": 2
    }
    return json.dumps(status, indent=2)


@mcp.resource("info://capabilities")
def get_capabilities_info() -> str:
    """Get detailed information about server capabilities."""
    info = {
        "tools": {
            "calculator": ["add", "multiply", "divide", "power"],
            "utility": ["get_current_time", "echo"]
        },
        "resources": {
            "config": "Server configuration",
            "status": "Health status",
            "capabilities": "This information"
        },
        "prompts": {
            "code_review": "Template for code review",
            "explain_code": "Template for code explanation"
        }
    }
    return json.dumps(info, indent=2)


# Prompts
@mcp.prompt()
def code_review(code: str, language: str = "python") -> str:
    """Generate a code review prompt."""
    return f"""Please review the following {language} code:

```{language}
{code}
```

Please provide feedback on:
1. Code quality and readability
2. Potential bugs or issues
3. Performance considerations
4. Best practices and improvements
5. Security considerations (if applicable)

Provide specific, actionable feedback with examples where possible."""


@mcp.prompt()
def explain_code(code: str, language: str = "python") -> str:
    """Generate a code explanation prompt."""
    return f"""Please explain the following {language} code in detail:

```{language}
{code}
```

Please explain:
1. What the code does
2. How it works step by step
3. Any important concepts or patterns used
4. The purpose of each major section
5. Any potential edge cases or limitations

Use clear, simple language suitable for someone learning {language}."""


if __name__ == "__main__":
    print("🚀 Starting Simple Example MCP Server...")
    print("This server provides:")
    print("  📊 Tools: Calculator functions (add, multiply, divide, power)")
    print("  📖 Resources: Server config, status, and capabilities info")
    print("  💬 Prompts: Code review and explanation templates")
    print()
    print("Use the MCP client to connect:")
    print(f"  mcp-client -s {__file__}")
    print()
    
    mcp.run() 