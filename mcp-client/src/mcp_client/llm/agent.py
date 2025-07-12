"""
MCP Agent implementation for intelligent tool calling.

This module provides the main agent that combines LLM providers
with MCP tools for intelligent conversation and automatic tool execution.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .providers import get_llm_provider, LLMProvider
from .tools import ToolManager, create_tool_manager
from ..database.models import ChatRequest, ChatResponse


class MCPAgent:
    """Intelligent agent that combines LLM capabilities with MCP tools."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_manager: ToolManager,
        system_prompt: str = None
    ):
        """
        Initialize MCP agent.
        
        Args:
            llm_provider: LLM provider instance
            tool_manager: Tool manager instance
            system_prompt: Optional system prompt
        """
        self.llm_provider = llm_provider
        self.tool_manager = tool_manager
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.conversation_history = []
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the agent."""
        tools_summary = self.tool_manager.get_tool_summary()
        
        return f"""You are an intelligent assistant with access to MCP (Model Context Protocol) tools.

Available tools: {', '.join(tools_summary['tool_names'])}
Tool categories: {list(tools_summary['tools_by_category'].keys())}

You can help users by:
1. Answering questions using your knowledge
2. Using available tools when they would be helpful
3. Explaining what tools you're using and why
4. Providing clear, helpful responses

When using tools:
- Choose the most appropriate tool for the task
- Provide clear explanations of what you're doing
- Handle errors gracefully and explain any issues
- Use multiple tools if needed to complete complex tasks

Be helpful, accurate, and transparent about your capabilities and limitations."""
    
    async def chat(
        self,
        message: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        max_tool_calls: int = 5
    ) -> Dict[str, Any]:
        """
        Process a chat message with intelligent tool calling.
        
        Args:
            message: User message
            model: LLM model to use
            temperature: Response temperature
            max_tokens: Maximum tokens in response
            max_tool_calls: Maximum number of tool calls per response
            
        Returns:
            Chat response with content and execution details
        """
        start_time = datetime.utcnow()
        
        try:
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": message
            })
            
            # Prepare messages for LLM
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            # Get available tools
            available_tools = self.tool_manager.get_tools_for_llm()
            
            # Track tool execution results
            tool_executions = []
            response_content = ""
            total_tokens = 0
            
            # Iterative tool calling loop
            for iteration in range(max_tool_calls):
                # Get LLM response
                llm_response = await self.llm_provider.chat_completion(
                    messages=messages,
                    tools=available_tools if available_tools else None,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Update token count
                if "usage" in llm_response:
                    total_tokens += llm_response["usage"].get("total_tokens", 0)
                
                # Check if LLM wants to use tools
                if llm_response.get("tool_calls"):
                    # Execute tool calls
                    tool_results = await self.tool_manager.execute_multiple_tools(
                        llm_response["tool_calls"]
                    )
                    
                    tool_executions.extend(tool_results)
                    
                    # Add assistant message with tool calls - format depends on provider
                    assistant_message = {
                        "role": "assistant",
                        "content": llm_response.get("content") or ""
                    }
                    
                    # Format tool calls for OpenAI (other providers don't need this in messages)
                    if self.llm_provider.__class__.__name__ == "OpenAIProvider":
                        if llm_response.get("tool_calls"):
                            formatted_tool_calls = []
                            for tool_call in llm_response["tool_calls"]:
                                formatted_tool_call = {
                                    "id": tool_call.get("id", f"call_{len(formatted_tool_calls)}"),
                                    "type": "function",
                                    "function": {
                                        "name": tool_call["name"],
                                        "arguments": json.dumps(tool_call["arguments"])
                                    }
                                }
                                formatted_tool_calls.append(formatted_tool_call)
                            assistant_message["tool_calls"] = formatted_tool_calls
                    
                    messages.append(assistant_message)
                    
                    # Add tool results - format depends on provider
                    if self.llm_provider.__class__.__name__ == "OpenAIProvider":
                        # OpenAI format: use "tool" role with tool_call_id
                        for i, tool_result in enumerate(tool_results):
                            tool_call_id = llm_response["tool_calls"][i].get("id", f"call_{i}")
                            if tool_result["success"]:
                                tool_message = {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": str(tool_result['result'])
                                }
                            else:
                                tool_message = {
                                    "role": "tool", 
                                    "tool_call_id": tool_call_id,
                                    "content": f"Error: {tool_result['error']}"
                                }
                            messages.append(tool_message)
                    else:
                        # Anthropic/Bedrock format: use "user" role with descriptive content
                        for tool_result in tool_results:
                            if tool_result["success"]:
                                tool_message = {
                                    "role": "user",
                                    "content": f"Tool {tool_result['tool_name']} result: {tool_result['result']}"
                                }
                            else:
                                tool_message = {
                                    "role": "user",
                                    "content": f"Tool {tool_result['tool_name']} error: {tool_result['error']}"
                                }
                            messages.append(tool_message)
                    
                    # Continue to get final response
                    continue
                else:
                    # No more tool calls, this is the final response
                    response_content = llm_response.get("content", "")
                    break
            
            # Add assistant response to conversation history
            if response_content:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_content
                })
            
            # Calculate total execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "response": response_content,
                "tool_calls": tool_executions,
                "execution_time": int(execution_time),
                "tokens_used": total_tokens,
                "iterations": iteration + 1,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "tool_calls": [],
                "execution_time": int(execution_time),
                "tokens_used": 0,
                "error": str(e),
                "timestamp": start_time.isoformat()
            }
    
    async def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()
    
    def set_system_prompt(self, system_prompt: str):
        """Update the system prompt."""
        self.system_prompt = system_prompt
    
    async def get_tool_info(self) -> Dict[str, Any]:
        """Get information about available tools."""
        return self.tool_manager.get_tool_summary()
    
    async def refresh_tools(self):
        """Refresh available tools from the MCP server."""
        await self.tool_manager.refresh_tools()
        # Update system prompt with new tools
        self.system_prompt = self._get_default_system_prompt()
    
    async def execute_tool_directly(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool directly without LLM interaction."""
        return await self.tool_manager.execute_tool(tool_name, arguments)


async def create_mcp_agent(
    server_config: Dict[str, Any],
    llm_config: Dict[str, Any],
    system_prompt: str = None
) -> MCPAgent:
    """
    Create and initialize an MCP agent.
    
    Args:
        server_config: MCP server configuration
        llm_config: LLM provider configuration
        system_prompt: Optional custom system prompt
        
    Returns:
        Initialized MCPAgent instance
    """
    # Create tool manager
    tool_manager = await create_tool_manager(server_config)
    
    # Create LLM provider
    provider_name = llm_config.get("provider", "openai")
    provider_kwargs = llm_config.get("kwargs", {})
    llm_provider = get_llm_provider(provider_name, **provider_kwargs)
    
    # Create agent
    agent = MCPAgent(llm_provider, tool_manager, system_prompt)
    
    return agent


class AgentManager:
    """Manages multiple MCP agents for different servers."""
    
    def __init__(self):
        """Initialize agent manager."""
        self.agents: Dict[int, MCPAgent] = {}
    
    async def create_agent(
        self,
        server_id: int,
        server_config: Dict[str, Any],
        llm_config: Dict[str, Any],
        system_prompt: str = None
    ) -> MCPAgent:
        """Create and register an agent for a server."""
        agent = await create_mcp_agent(server_config, llm_config, system_prompt)
        self.agents[server_id] = agent
        return agent
    
    def get_agent(self, server_id: int) -> Optional[MCPAgent]:
        """Get agent for a server."""
        return self.agents.get(server_id)
    
    async def remove_agent(self, server_id: int):
        """Remove agent for a server."""
        if server_id in self.agents:
            agent = self.agents[server_id]
            # Close MCP client connection
            if hasattr(agent.tool_manager.mcp_client, 'close'):
                await agent.tool_manager.mcp_client.close()
            del self.agents[server_id]
    
    def list_agents(self) -> List[int]:
        """List all registered agent server IDs."""
        return list(self.agents.keys())
    
    async def refresh_all_agents(self):
        """Refresh tools for all agents."""
        for agent in self.agents.values():
            try:
                await agent.refresh_tools()
            except Exception as e:
                print(f"Error refreshing agent: {e}")


# Global agent manager
agent_manager = AgentManager()


def get_agent_manager() -> AgentManager:
    """Get the global agent manager."""
    return agent_manager 