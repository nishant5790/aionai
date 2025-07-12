"""
Main Streamlit web interface for MCP Client.

This module provides a user-friendly web interface for managing
MCP servers and running intelligent conversations.
"""

import streamlit as st
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

import requests
import pandas as pd

# Configure page
st.set_page_config(
    page_title="MCP Client",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """Make API request to the FastAPI backend."""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {"error": str(e)}


def main():
    """Main Streamlit application."""
    
    # Sidebar navigation
    st.sidebar.title("🔗 MCP Client")
    st.sidebar.markdown("---")
    
    # Page selection
    page = st.sidebar.selectbox(
        "Navigate",
        ["🏠 Dashboard", "🖥️ Servers", "💬 Chat", "📊 History", "⚙️ Settings"]
    )
    
    # API health check
    try:
        health = api_request("GET", "/health/")
        if "error" not in health:
            st.sidebar.success("🟢 API Connected")
        else:
            st.sidebar.error("🔴 API Disconnected")
    except:
        st.sidebar.error("🔴 API Unavailable")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick Actions**")
    
    if st.sidebar.button("🔄 Refresh"):
        st.rerun()
    
    # Main content based on selected page
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🖥️ Servers":
        show_servers()
    elif page == "💬 Chat":
        show_chat()
    elif page == "📊 History":
        show_history()
    elif page == "⚙️ Settings":
        show_settings()


def show_dashboard():
    """Show the main dashboard."""
    st.title("🏠 MCP Client Dashboard")
    st.markdown("Welcome to the Model Context Protocol Client!")
    
    # Get system info
    try:
        info = api_request("GET", "/info")
        health = api_request("GET", "/health/detailed")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Service", "MCP Client API")
            st.metric("Version", info.get("version", "Unknown"))
        
        with col2:
            servers = api_request("GET", "/servers/")
            if isinstance(servers, list):
                st.metric("MCP Servers", len(servers))
                active_servers = len([s for s in servers if s.get("is_active", False)])
                st.metric("Active Servers", active_servers)
            else:
                st.metric("MCP Servers", "Error")
        
        with col3:
            if "error" not in health:
                status = health.get("status", "unknown")
                if status == "healthy":
                    st.metric("System Status", "🟢 Healthy")
                else:
                    st.metric("System Status", "🟢 Healthy")
            else:
                st.metric("System Status", "🔴 Error")
        
        # Recent activity
        st.subheader("📈 Recent Activity")
        history = api_request("GET", "/queries/history", params={"limit": 10})
        
        if isinstance(history, list) and history:
            df = pd.DataFrame(history)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at', ascending=False)
            
            st.dataframe(
                df[['query_type', 'query_text', 'execution_time', 'created_at']],
                use_container_width=True
            )
        else:
            st.info("No recent activity found.")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")


def show_servers():
    """Show MCP server management interface."""
    st.title("🖥️ MCP Servers")
    
    # Add new server section
    with st.expander("➕ Add New Server", expanded=False):
        with st.form("add_server"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Server Name", placeholder="My MCP Server")
                description = st.text_area("Description", placeholder="What does this server do?")
                server_type = st.selectbox("Transport Type", ["stdio", "sse", "streamable_http"])
            
            with col2:
                server_command = st.text_input("Command", placeholder="python")
                server_path = st.text_input("Script Path", placeholder="path/to/server.py")
                server_args = st.text_input("Arguments (JSON)", placeholder='["arg1", "arg2"]')
                server_env = st.text_input("Environment (JSON)", placeholder='{"KEY": "value"}')
            
            submitted = st.form_submit_button("Add Server")
            
            if submitted:
                try:
                    server_data = {
                        "name": name,
                        "description": description,
                        "server_type": server_type,
                        "server_command": server_command,
                        "server_path": server_path if server_path else None,
                        "server_args": json.loads(server_args) if server_args else [],
                        "server_env": json.loads(server_env) if server_env else {}
                    }
                    
                    result = api_request("POST", "/servers/", data=server_data)
                    
                    if "error" not in result:
                        st.success(f"Server '{name}' added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to add server: {result['error']}")
                        
                except json.JSONDecodeError:
                    st.error("Invalid JSON in arguments or environment fields")
                except Exception as e:
                    st.error(f"Error adding server: {str(e)}")
    
    # List existing servers
    st.subheader("📋 Your Servers")
    
    servers = api_request("GET", "/servers/")
    
    if isinstance(servers, list):
        if not servers:
            st.info("No servers configured yet. Add your first server above!")
        else:
            for server in servers:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        status_icon = "🟢" if server.get("is_active") else "🔴"
                        st.write(f"{status_icon} **{server['name']}**")
                        if server.get("description"):
                            st.caption(server["description"])
                    
                    with col2:
                        st.write(f"Type: {server['server_type']}")
                        if server.get("capabilities"):
                            tools_count = len(server["capabilities"].get("tools", []))
                            st.write(f"Tools: {tools_count}")
                    
                    with col3:
                        if st.button(f"Test Connection", key=f"test_{server['id']}"):
                            test_result = api_request("POST", f"/servers/{server['id']}/test")
                            if test_result.get("status") == "success":
                                st.success("✅ Connection successful!")
                            else:
                                st.error(f"❌ {test_result.get('message', 'Connection failed')}")
                        
                        if st.button(f"Discover Tools", key=f"discover_{server['id']}"):
                            discover_result = api_request("POST", f"/servers/{server['id']}/discover")
                            if "error" not in discover_result:
                                st.success("🔍 Capabilities discovered!")
                                st.rerun()
                            else:
                                st.error(f"❌ {discover_result.get('detail', 'Discovery failed')}")
                    
                    with col4:
                        if st.button(f"🗑️", key=f"delete_{server['id']}", help="Delete server"):
                            if st.session_state.get(f"confirm_delete_{server['id']}", False):
                                delete_result = api_request("DELETE", f"/servers/{server['id']}")
                                if "error" not in delete_result:
                                    st.success("Server deleted!")
                                    st.rerun()
                                else:
                                    st.error("Delete failed!")
                            else:
                                st.session_state[f"confirm_delete_{server['id']}"] = True
                                st.warning("Click again to confirm deletion")
                    
                    # Show capabilities if available
                    if server.get("capabilities"):
                        with st.expander(f"🛠️ Capabilities for {server['name']}", expanded=False):
                            caps = server["capabilities"]
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if caps.get("tools"):
                                    st.write("**Tools:**")
                                    for tool in caps["tools"]:
                                        st.write(f"• {tool['name']}")
                            
                            with col2:
                                if caps.get("resources"):
                                    st.write("**Resources:**")
                                    for resource in caps["resources"]:
                                        st.write(f"• {resource['uri']}")
                            
                            with col3:
                                if caps.get("prompts"):
                                    st.write("**Prompts:**")
                                    for prompt in caps["prompts"]:
                                        st.write(f"• {prompt['name']}")
                    
                    st.markdown("---")
    else:
        st.error("Failed to load servers")


def show_chat():
    """Show the chat interface."""
    st.title("💬 Intelligent Chat")
    
    # Server selection
    servers = api_request("GET", "/servers/")
    
    if not isinstance(servers, list) or not servers:
        st.warning("No servers available. Please add a server first in the Servers section.")
        return
    
    # Filter active servers
    active_servers = [s for s in servers if s.get("is_active", False)]
    
    if not active_servers:
        st.warning("No active servers found. Please check your server configurations.")
        return
    
    # Server and LLM selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_server = st.selectbox(
            "Select MCP Server",
            active_servers,
            format_func=lambda x: x["name"]
        )
    
    with col2:
        llm_provider = st.selectbox(
            "LLM Provider",
            ["openai", "anthropic", "bedrock"]
        )
    
    with col3:
        model_options = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
            "bedrock": ["anthropic.claude-3-5-sonnet-20241022-v2:0"]
        }
        
        model_name = st.selectbox(
            "Model",
            model_options.get(llm_provider, ["gpt-4o"])
        )
    
    # System prompt customization
    with st.expander("🎯 System Prompt", expanded=False):
        system_prompt = st.text_area(
            "Custom System Prompt (optional)",
            placeholder="You are a helpful assistant with access to MCP tools...",
            height=100
        )
    
    # Chat interface
    st.subheader(f"Chat with {selected_server['name']}")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Show conversation history
    if st.session_state.chat_history:
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    
                    # Show tool calls if any
                    if message.get("tool_calls"):
                        with st.expander("🛠️ Tool Calls", expanded=False):
                            for tool_call in message["tool_calls"]:
                                st.json(tool_call)
    
    # Chat input
    user_message = st.chat_input("Type your message here...")
    
    if user_message:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Show user message
        with st.chat_message("user"):
            st.write(user_message)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_data = {
                    "message": user_message,
                    "mcp_server_id": selected_server["id"],
                    "llm_provider": llm_provider,
                    "model_name": model_name,
                    "system_prompt": system_prompt if system_prompt else None
                }
                
                response = api_request("POST", f"/chat/{selected_server['id']}", data=chat_data)
                
                if "error" not in response:
                    st.write(response["response"])
                    
                    # Show execution details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Execution Time", f"{response.get('execution_time', 0)}ms")
                    with col2:
                        st.metric("Tokens Used", response.get("tokens_used", 0))
                    with col3:
                        st.metric("Tool Calls", len(response.get("tool_calls", [])))
                    
                    # Show tool calls
                    if response.get("tool_calls"):
                        with st.expander("🛠️ Tool Execution Details", expanded=False):
                            for tool_call in response["tool_calls"]:
                                st.json(tool_call)
                    
                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response["response"],
                        "tool_calls": response.get("tool_calls", [])
                    })
                
                else:
                    st.error(f"Chat failed: {response.get('detail', 'Unknown error')}")
    
    # Chat controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reset Conversation"):
            reset_result = api_request("POST", f"/chat/{selected_server['id']}/reset")
            if "error" not in reset_result:
                st.session_state.chat_history = []
                st.success("Conversation reset!")
                st.rerun()
    
    with col2:
        if st.button("📊 View Tools"):
            tools = api_request("GET", f"/chat/{selected_server['id']}/tools")
            if "error" not in tools:
                st.json(tools)


def show_history():
    """Show query history."""
    st.title("📊 Query History")
    
    # Get query history
    history = api_request("GET", "/queries/history", params={"limit": 100})
    
    if isinstance(history, list):
        if not history:
            st.info("No query history found.")
        else:
            # Convert to DataFrame for better display
            df = pd.DataFrame(history)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at', ascending=False)
            
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                query_types = df['query_type'].unique().tolist()
                selected_types = st.multiselect("Filter by Type", query_types, default=query_types)
            
            with col2:
                date_range = st.date_input("Date Range", value=[])
            
            with col3:
                search_term = st.text_input("Search in queries")
            
            # Apply filters
            filtered_df = df[df['query_type'].isin(selected_types)]
            
            if search_term:
                filtered_df = filtered_df[
                    filtered_df['query_text'].str.contains(search_term, case=False, na=False)
                ]
            
            # Display results
            st.dataframe(
                filtered_df[['query_type', 'query_text', 'execution_time', 'created_at']],
                use_container_width=True
            )
            
            # Query details
            if len(filtered_df) > 0:
                selected_query = st.selectbox(
                    "View Query Details",
                    filtered_df.index,
                    format_func=lambda x: f"{filtered_df.loc[x, 'query_type']}: {filtered_df.loc[x, 'query_text'][:50]}..."
                )
                
                if selected_query is not None:
                    query_details = filtered_df.loc[selected_query]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Query Information:**")
                        st.write(f"Type: {query_details['query_type']}")
                        st.write(f"Text: {query_details['query_text']}")
                        st.write(f"Execution Time: {query_details['execution_time']}ms")
                        st.write(f"Created: {query_details['created_at']}")
                    
                    with col2:
                        st.write("**Result:**")
                        if query_details['result']:
                            st.json(query_details['result'])
                        elif query_details['error_message']:
                            st.error(f"Error: {query_details['error_message']}")
                        else:
                            st.write("No result data")
    
    else:
        st.error("Failed to load query history")


def show_settings():
    """Show application settings."""
    st.title("⚙️ Settings")
    
    st.subheader("🔧 Configuration")
    
    # API settings
    st.write("**API Configuration:**")
    st.write(f"API Base URL: `{API_BASE_URL}`")
    
    # Environment variables
    st.subheader("🌍 Environment Variables")
    
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "Not set"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "Not set"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID", "Not set"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY", "Not set"),
        "DATABASE_URL": os.getenv("DATABASE_URL", "Not set")
    }
    
    for key, value in env_vars.items():
        is_set = value != "Not set" and len(value) > 0
        status = "✅" if is_set else "❌"
        masked_value = "*" * len(value) if is_set and "KEY" in key else value
        st.write(f"{status} `{key}`: {masked_value}")
    
    # System information
    st.subheader("ℹ️ System Information")
    
    try:
        health = api_request("GET", "/health/detailed")
        if "error" not in health:
            if "components" in health:
                st.json(health["components"])
            if "environment" in health:
                st.json(health["environment"])
    except:
        st.error("Could not retrieve system information")
    
    # Clear data
    st.subheader("🗑️ Data Management")
    
    if st.button("Clear Chat History", type="secondary"):
        st.session_state.chat_history = []
        st.success("Chat history cleared!")


if __name__ == "__main__":
    main() 