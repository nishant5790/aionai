#!/usr/bin/env python3
"""
Comprehensive Demo of MCP Client with LLM Integration.

This script demonstrates how to use the MCP client with various LLM providers
for intelligent tool calling and conversation management.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client.llm.agent import create_mcp_agent
from mcp_client.database.database import init_database


async def demo_basic_mcp_connection():
    """Demo basic MCP server connection and tool discovery."""
    print("🔗 Demo 1: Basic MCP Connection and Tool Discovery")
    print("=" * 60)
    
    # Server configuration for our demo server
    server_config = {
        "server_command": "python",
        "server_args": ["examples/simple_server.py"],
        "server_env": {},
        "server_type": "stdio"
    }
    
    # LLM configuration (using OpenAI as default)
    llm_config = {
        "provider": "openai",
        "kwargs": {
            "api_key": os.getenv("OPENAI_API_KEY", ".")
        }
    }
    
    try:
        # Create agent
        print("📡 Connecting to MCP server...")
        agent = await create_mcp_agent(server_config, llm_config)
        
        # Get tool information
        tool_info = await agent.get_tool_info()
        
        print(f"✅ Connected successfully!")
        print(f"📊 Found {tool_info['total_tools']} tools")
        print(f"🏷️  Categories: {list(tool_info['tools_by_category'].keys())}")
        
        for category, tools in tool_info['tools_by_category'].items():
            print(f"   {category}: {', '.join(tools)}")
        
        # Close connection
        await agent.tool_manager.mcp_client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


async def demo_direct_tool_execution():
    """Demo direct tool execution without LLM."""
    print("🛠️  Demo 2: Direct Tool Execution")
    print("=" * 60)
    
    server_config = {
        "server_command": "python",
        "server_args": ["examples/simple_server.py"],
        "server_env": {},
        "server_type": "stdio"
    }
    
    llm_config = {
        "provider": "openai",
        "kwargs": {"api_key": ""}
    }
    
    try:
        agent = await create_mcp_agent(server_config, llm_config)
        
        # Execute calculator tools
        calculations = [
            {"tool": "add", "args": {"a": 15, "b": 27}},
            {"tool": "multiply", "args": {"a": 8, "b": 9}},
            {"tool": "divide", "args": {"a": 100, "b": 4}},
        ]
        
        for calc in calculations:
            print(f"🧮 Executing {calc['tool']}({calc['args']})...")
            result = await agent.execute_tool_directly(calc['tool'], calc['args'])
            
            if result['success']:
                print(f"   ✅ Result: {result['result']}")
                print(f"   ⏱️  Execution time: {result['execution_time_ms']}ms")
            else:
                print(f"   ❌ Error: {result['error']}")
        
        await agent.tool_manager.mcp_client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


async def demo_intelligent_conversation():
    """Demo intelligent conversation with automatic tool calling."""
    print("🤖 Demo 3: Intelligent Conversation with Tool Calling")
    print("=" * 60)
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "demo-key":
        print("⚠️  OpenAI API key not found. Skipping intelligent conversation demo.")
        print("   Set OPENAI_API_KEY environment variable to run this demo.")
        return
    
    server_config = {
        "server_command": "python",
        "server_args": ["examples/simple_server.py"],
        "server_env": {},
        "server_type": "stdio"
    }
    
    llm_config = {
        "provider": "openai",
        "kwargs": {
            "api_key": api_key
        }
    }
    
    try:
        agent = await create_mcp_agent(server_config, llm_config)
        
        # Test conversations
        conversations = [
            "What's 15 + 27?",
            "Can you multiply 8 by 9?",
            "What's the current status of the server?",
            "Calculate 15 + 27, then multiply the result by 2",
        ]
        
        for i, message in enumerate(conversations, 1):
            print(f"💭 Conversation {i}:")
            print(f"   User: {message}")
            
            response = await agent.chat(
                message=message,
                model="gpt-4o-mini",  # Use cheaper model for demo
                temperature=0.1
            )
            
            print(f"   🤖 Assistant: {response['response']}")
            
            if response.get('tool_calls'):
                print(f"   🛠️  Tools used: {len(response['tool_calls'])}")
                for tool_call in response['tool_calls']:
                    if tool_call['success']:
                        print(f"      ✅ {tool_call['tool_name']}: {tool_call['result']}")
                    else:
                        print(f"      ❌ {tool_call['tool_name']}: {tool_call['error']}")
            
            print(f"   ⏱️  Execution time: {response['execution_time']}ms")
            print(f"   🎯 Tokens used: {response.get('tokens_used', 0)}")
            print()
        
        await agent.tool_manager.mcp_client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_multiple_providers():
    """Demo multiple LLM providers (if API keys are available)."""
    print("🌐 Demo 4: Multiple LLM Providers")
    print("=" * 60)
    
    server_config = {
        "server_command": "python",
        "server_args": ["examples/simple_server.py"],
        "server_env": {},
        "server_type": "stdio"
    }
    
    # Test OpenAI with hardcoded key
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    providers = [
        ("openai", openai_key, "gpt-4o-mini", {"api_key": openai_key}),
        ("anthropic", os.getenv("ANTHROPIC_API_KEY"), "claude-3-haiku-20240307", {}),
        ("bedrock", os.getenv("AWS_ACCESS_KEY_ID"), "anthropic.claude-3-haiku-20240307-v1:0", {})
    ]
    
    test_message = "What's 12 + 8?"
    
    for provider_name, api_key, model, provider_kwargs in providers:
        print(f"🔮 Testing {provider_name.upper()}...")
        
        if not api_key or (provider_name == "openai" and api_key == "demo-key"):
            print(f"   ⚠️  API key not available, skipping {provider_name}")
            continue
        
        llm_config = {
            "provider": provider_name,
            "kwargs": provider_kwargs
        }
        
        try:
            agent = await create_mcp_agent(server_config, llm_config)
            
            response = await agent.chat(
                message=test_message,
                model=model,
                temperature=0.1
            )
            
            print(f"   ✅ Response: {response['response']}")
            print(f"   🛠️  Tool calls: {len(response.get('tool_calls', []))}")
            print(f"   ⏱️  Time: {response['execution_time']}ms")
            
            await agent.tool_manager.mcp_client.close()
            
        except Exception as e:
            print(f"   ❌ Error with {provider_name}: {e}")
        
        print()


async def demo_persistent_conversation():
    """Demo persistent conversation with history."""
    print("💾 Demo 5: Persistent Conversation with History")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "demo-key":
        print("⚠️  OpenAI API key not found. Skipping persistent conversation demo.")
        return
    
    server_config = {
        "server_command": "python",
        "server_args": ["examples/simple_server.py"],
        "server_env": {},
        "server_type": "stdio"
    }
    
    llm_config = {
        "provider": "openai",
        "kwargs": {
            "api_key": api_key
        }
    }
    
    try:
        agent = await create_mcp_agent(server_config, llm_config)
        
        # Multi-turn conversation
        conversation = [
            "Hi! Please calculate 10 + 5 for me.",
            "Now multiply that result by 3.",
            "What was the first number I asked you to calculate with?",
            "Can you show me the server status?"
        ]
        
        for i, message in enumerate(conversation, 1):
            print(f"🔄 Turn {i}:")
            print(f"   User: {message}")
            
            response = await agent.chat(message=message, model="gpt-4o-mini")
            
            print(f"   🤖 Assistant: {response['response']}")
            
            if response.get('tool_calls'):
                print(f"   🛠️  Tools: {[tc['tool_name'] for tc in response['tool_calls']]}")
            
            print()
        
        # Show conversation history
        history = agent.get_conversation_history()
        print(f"📚 Conversation History ({len(history)} messages):")
        for msg in history:
            role_icon = "👤" if msg['role'] == 'user' else "🤖"
            print(f"   {role_icon} {msg['content'][:60]}...")
        
        await agent.tool_manager.mcp_client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all demos."""
    print("🚀 MCP Client with LLM Integration - Comprehensive Demo")
    print("=" * 70)
    print()
    
    # Initialize database
    print("🗄️  Initializing database...")
    init_database()
    print("✅ Database ready!")
    print()
    
    # Run all demos
    await demo_basic_mcp_connection()
    await demo_direct_tool_execution()
    await demo_intelligent_conversation()
    await demo_multiple_providers()
    await demo_persistent_conversation()
    
    print("🎉 Demo completed!")
    print()
    print("Next steps:")
    print("1. 🌐 Start the web interface: python deployment/run_server.py")
    print("2. 📖 View API docs: http://localhost:8000/docs")
    print("3. 💬 Use the chat interface: http://localhost:8501")
    print("4. 🔧 Configure your own MCP servers")
    print("5. 🤖 Experiment with different LLM providers")


if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        sys.exit(1) 