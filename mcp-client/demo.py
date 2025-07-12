#!/usr/bin/env python3
"""
Demo script showing how to use the MCP Client programmatically.

This script demonstrates all the key features of the MCP client:
- Connecting to servers
- Discovering capabilities
- Calling tools
- Reading resources
- Getting prompts
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import the client
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client import MCPClient, MCPClientConfig


async def demo_mcp_client():
    """Demonstrate MCP client capabilities."""
    print("🚀 MCP Client Demo")
    print("=" * 50)
    
    # Configure the client
    config = MCPClientConfig(
        transport_type="stdio",
        debug=False
    )
    
    # Create and use the client
    async with MCPClient(config) as client:
        try:
            print("\n1. 🔄 Connecting to example server...")
            await client.connect("examples/simple_server.py")
            print("   ✅ Connected successfully!")
            
            print("\n2. 🔍 Discovering capabilities...")
            await client.discover_capabilities()
            print(f"   📊 Found {len(client.available_tools)} tools")
            print(f"   📚 Found {len(client.available_resources)} resources") 
            print(f"   💬 Found {len(client.available_prompts)} prompts")
            
            print("\n3. 🛠️  Testing tool calls...")
            
            # Test calculator tools
            result = await client.call_tool("add", {"a": 10, "b": 5})
            print(f"   add(10, 5) = {result.content[0].text}")
            
            result = await client.call_tool("multiply", {"a": 7, "b": 6})
            print(f"   multiply(7, 6) = {result.content[0].text}")
            
            result = await client.call_tool("power", {"base": 2, "exponent": 8})
            print(f"   power(2, 8) = {result.content[0].text}")
            
            # Test utility tools
            result = await client.call_tool("echo", {"message": "Hello from demo!"})
            print(f"   echo('Hello from demo!') = {result.content[0].text}")
            
            result = await client.call_tool("get_current_time", {})
            print(f"   get_current_time() = {result.content[0].text}")
            
            print("\n4. 📖 Testing resource reading...")
            
            # Read configuration
            result = await client.read_resource("config://server")
            config_text = result.contents[0].text
            print(f"   config://server = {config_text[:100]}...")
            
            # Read status
            result = await client.read_resource("status://health")
            status_text = result.contents[0].text
            print(f"   status://health = {status_text[:100]}...")
            
            print("\n5. 💬 Testing prompt generation...")
            
            # Generate code review prompt
            result = await client.get_prompt("code_review", {
                "code": "def factorial(n):\n    return n * factorial(n-1) if n > 1 else 1",
                "language": "python"
            })
            prompt_text = result.messages[0].content.text
            print(f"   code_review prompt = {prompt_text[:150]}...")
            
            print("\n🎉 Demo completed successfully!")
            print("\nThe MCP client successfully demonstrated:")
            print("  ✅ Server connection via stdio transport")
            print("  ✅ Capability discovery (tools, resources, prompts)")
            print("  ✅ Tool execution with various data types")
            print("  ✅ Resource reading with different URI schemes")
            print("  ✅ Prompt generation with parameters")
            print("  ✅ Error handling and connection management")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("Starting MCP Client Demo...")
    print("Make sure the virtual environment is activated and dependencies are installed.")
    print()
    
    asyncio.run(demo_mcp_client()) 