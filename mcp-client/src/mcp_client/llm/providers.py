"""
LLM provider implementations for MCP Client.

This module provides implementations for different LLM providers
including OpenAI, Anthropic, and AWS Bedrock.
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import openai
from anthropic import Anthropic
import boto3

from ..database.models import ChatRequest, ChatResponse


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a chat completion with optional tool calling."""
        pass
    
    @abstractmethod
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP tools for the specific provider."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: str = None):
        """Initialize OpenAI provider."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP tools for OpenAI function calling."""
        formatted_tools = []
        
        for tool in tools:
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {})
                }
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "gpt-4o",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion using OpenAI."""
        try:
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000)
            }
            
            # Add tools if provided
            if tools:
                formatted_tools = self.format_tools_for_provider(tools)
                if formatted_tools:
                    request_params["tools"] = formatted_tools
                    request_params["tool_choice"] = "auto"
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract response
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": [],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            # Handle tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })
            
            return result
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: str = None):
        """Initialize Anthropic provider."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = Anthropic(api_key=self.api_key)
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP tools for Anthropic tool calling."""
        formatted_tools = []
        
        for tool in tools:
            formatted_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {})
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion using Anthropic."""
        try:
            # Prepare messages (Anthropic format)
            formatted_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            if system_message:
                request_params["system"] = system_message
            
            # Add tools if provided
            if tools:
                formatted_tools = self.format_tools_for_provider(tools)
                if formatted_tools:
                    request_params["tools"] = formatted_tools
            
            # Make API call
            response = await asyncio.to_thread(
                self.client.messages.create,
                **request_params
            )
            
            # Extract response
            result = {
                "content": "",
                "tool_calls": [],
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }
            
            # Process content blocks
            for content_block in response.content:
                if content_block.type == "text":
                    result["content"] += content_block.text
                elif content_block.type == "tool_use":
                    result["tool_calls"].append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "arguments": content_block.input
                    })
            
            return result
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider implementation."""
    
    def __init__(self, region_name: str = "us-east-1", access_key: str = None, secret_key: str = None):
        """Initialize Bedrock provider."""
        self.region_name = region_name
        
        # Initialize boto3 client
        session_kwargs = {"region_name": region_name}
        if access_key and secret_key:
            session_kwargs.update({
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key
            })
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client("bedrock-runtime")
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP tools for Bedrock (using Anthropic Claude format)."""
        formatted_tools = []
        
        for tool in tools:
            formatted_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {})
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "us.anthropic.claude-opus-4-20250514-v1:0",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion using AWS Bedrock."""
        try:
            # Prepare request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "messages": []
            }
            
            # Format messages
            system_message = None
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    request_body["messages"].append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            if system_message:
                request_body["system"] = system_message
            
            # Add tools if provided
            if tools:
                formatted_tools = self.format_tools_for_provider(tools)
                if formatted_tools:
                    request_body["tools"] = formatted_tools
            
            # Make API call
            response = await asyncio.to_thread(
                self.client.invoke_model,
                modelId=model,
                body=json.dumps(request_body),
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            
            result = {
                "content": "",
                "tool_calls": [],
                "usage": {
                    "prompt_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response_body.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        response_body.get("usage", {}).get("input_tokens", 0) +
                        response_body.get("usage", {}).get("output_tokens", 0)
                    )
                }
            }
            
            # Process content
            for content_block in response_body.get("content", []):
                if content_block.get("type") == "text":
                    result["content"] += content_block.get("text", "")
                elif content_block.get("type") == "tool_use":
                    result["tool_calls"].append({
                        "id": content_block.get("id"),
                        "name": content_block.get("name"),
                        "arguments": content_block.get("input", {})
                    })
            
            return result
            
        except Exception as e:
            raise Exception(f"Bedrock API error: {str(e)}")


def get_llm_provider(provider_name: str, **kwargs) -> LLMProvider:
    """Factory function to get LLM provider instance."""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "bedrock": BedrockProvider
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return providers[provider_name](**kwargs) 