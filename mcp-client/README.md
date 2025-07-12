# MCP Client

A comprehensive Python client for connecting to and interacting with any Model Context Protocol (MCP) server, featuring **intelligent LLM integration**, **web interface**, and **REST API**.

## 🌟 Features

### 🔗 **Universal MCP Connectivity**
- **Multiple Transports**: stdio, SSE, streamable HTTP
- **Auto-detection**: Automatically detect the appropriate transport
- **Full MCP Support**: Tools, Resources, Prompts, and Capabilities discovery

### 🤖 **Intelligent LLM Integration**
- **Multi-Provider Support**: OpenAI GPT-4o, Anthropic Claude, AWS Bedrock
- **Automatic Tool Calling**: AI decides when and how to use MCP tools
- **Conversation Memory**: Persistent conversation history
- **Smart Routing**: Intelligent tool selection and execution

### 🌐 **Web Interface**
- **Beautiful Streamlit UI**: User-friendly web interface
- **Server Management**: Add, configure, and monitor MCP servers
- **Interactive Chat**: Real-time conversations with LLM + MCP integration
- **Query History**: Track and analyze all interactions
- **Multi-Provider Config**: Easy switching between LLM providers

### 📊 **REST API**
- **Complete API**: Full CRUD operations for servers and queries
- **OpenAPI Documentation**: Auto-generated docs at `/docs`
- **Real-time Monitoring**: Health checks and metrics
- **Async Support**: High-performance async endpoints

### 🎯 **Production Ready**
- **Database Integration**: SQLite/PostgreSQL support
- **Logging & Monitoring**: Comprehensive tracking
- **Error Handling**: Robust error management
- **Deployment Scripts**: Easy deployment and scaling

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-client

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

1. **CLI Interface** (Original functionality):
```bash
# List tools from an MCP server
mcp-client -s examples/simple_server.py list

# Execute a tool
mcp-client -s examples/simple_server.py tool add a=5 b=3

# Interactive mode
mcp-client -s examples/simple_server.py
```

2. **Web Interface** (NEW!):
```bash
# Start both API and web interface
python deployment/run_server.py

# Or start individually
python deployment/run_server.py --mode api    # API only
python deployment/run_server.py --mode web    # Web only
```

Then open:
- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

3. **Programmatic Usage with LLM** (NEW!):
```python
from mcp_client.llm.agent import create_mcp_agent

# Configure your MCP server
server_config = {
    "server_command": "python",
    "server_args": ["path/to/your/server.py"],
    "server_env": {},
    "server_type": "stdio"
}

# Configure LLM provider
llm_config = {
    "provider": "openai",  # or "anthropic", "bedrock"
    "kwargs": {}
}

# Create intelligent agent
agent = await create_mcp_agent(server_config, llm_config)

# Have a conversation with automatic tool calling
response = await agent.chat("What's 15 + 27 multiplied by 3?")
print(response["response"])  # AI will use tools automatically!
```

## 🧪 Demo

Run the comprehensive demo to see all features in action:

```bash
# Set your API keys (optional, demo works without them)
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-key"

# Run the demo
python agent_demo.py
```

The demo showcases:
- ✅ MCP server connection and tool discovery
- ✅ Direct tool execution
- ✅ Intelligent conversation with automatic tool calling
- ✅ Multiple LLM provider support
- ✅ Persistent conversation history

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │    FastAPI       │    │   MCP Client    │
│  Web Interface  │◄──►│   REST API       │◄──►│     Core        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │    Database      │    │  MCP Servers    │
                       │  (SQLite/PG)     │    │ (stdio/sse/http)│
                       └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────┐
                              │            LLM Providers            │
                              │  OpenAI • Anthropic • AWS Bedrock   │
                              └─────────────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./mcp_client.db

# API Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Web Interface
API_BASE_URL=http://localhost:8000
```

### Server Configuration

Add MCP servers via the web interface or API:

```json
{
  "name": "My Calculator Server",
  "description": "Python calculator with MCP tools",
  "server_type": "stdio",
  "server_command": "python",
  "server_args": ["path/to/calculator_server.py"],
  "server_env": {"DEBUG": "false"}
}
```

## 📖 API Reference

### Core Endpoints

- **Servers**: `GET/POST/PUT/DELETE /servers/`
- **Queries**: `POST /queries/{server_id}/tool`
- **Chat**: `POST /chat/{server_id}`
- **Health**: `GET /health/`

### LLM Integration Endpoints

- **Chat with Server**: `POST /chat/{server_id}`
- **Reset Conversation**: `POST /chat/{server_id}/reset`
- **Get History**: `GET /chat/{server_id}/history`
- **List Providers**: `GET /chat/providers`

See full documentation at: http://localhost:8000/docs

## 🎯 Use Cases

### 1. **AI-Powered Tool Orchestration**
Let AI automatically use your MCP tools based on natural language requests.

### 2. **Multi-Server Management**
Manage and monitor multiple MCP servers from a single interface.

### 3. **Conversational APIs**
Build chat interfaces that can interact with any MCP-enabled service.

### 4. **Development & Testing**
Test and debug MCP servers with comprehensive tooling.

### 5. **Production Deployments**
Deploy robust MCP client services with monitoring and logging.

## 🛠️ Development

### Project Structure

```
mcp-client/
├── src/mcp_client/           # Main package
│   ├── client.py             # Core MCP client
│   ├── main.py              # CLI interface
│   ├── api/                 # FastAPI application
│   ├── web/                 # Streamlit interface
│   ├── llm/                 # LLM integration
│   └── database/            # Database models
├── examples/                # Example servers
├── deployment/              # Deployment scripts
├── requirements.txt         # Dependencies
└── README.md               # This file
```

### Adding New LLM Providers

1. Implement the `LLMProvider` interface in `src/mcp_client/llm/providers.py`
2. Add provider configuration to `get_llm_provider()` function
3. Update the web interface provider options

### Creating Custom MCP Servers

See `examples/simple_server.py` for a template MCP server implementation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/mcp-client/issues)
- **Documentation**: [MCP Specification](https://modelcontextprotocol.io/)
- **Examples**: See `examples/` directory

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) specification
- [OpenAI](https://openai.com/) for GPT models
- [Anthropic](https://anthropic.com/) for Claude models
- [AWS Bedrock](https://aws.amazon.com/bedrock/) for hosted models
