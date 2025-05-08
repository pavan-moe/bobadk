from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import query

app = FastAPI(
    title="ADK Zendesk Search API",
    description="API for searching and answering questions using Zendesk ticket data",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, tags=["query"])

@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "ADK Zendesk Search API is running"}

@app.get("/agent-info", tags=["info"])
async def agent_info():
    """Provide information about the agent"""
    from src.agent.search_agent import SearchAgent
    agent = SearchAgent()
    return {
        "agent_name": agent.agent.name,
        "description": agent.agent.description,
        "model": agent.agent.model,
        "collection": agent.collection_name
    }

def run_fastapi():
    """Run the FastAPI server"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# MCP server functions
async def run_mcp_server():
    """Run as MCP server"""
    from mcp.server.stdio import stdio_server
    from mcp.server.models import InitializationOptions
    
    from src.agent.search_agent import SearchAgent
    from mcp import types as mcp_types
    from mcp.server.lowlevel import Server
    from google.adk.tools.function_tool import FunctionTool
    import json
    
    search_agent = SearchAgent()
    
    # Create MCP Server
    app = Server("zendesk-search-mcp-server")
    
    async def search(query: str, limit: int = 5) -> dict:
        """Search for information using Zendesk ticket data."""
        return search_agent.search(query, limit=limit)
    
    search_fn = FunctionTool(search)
    
    @app.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        """List available tools."""
        return [
            mcp_types.Tool(
                name="search",
                description="Search for information in Zendesk tickets",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "limit": {"type": "integer", "description": "Maximum number of results to return"}
                    },
                    "required": ["query"]
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
        """Execute a tool call."""
        if name == "search":
            try:
                query = arguments.get("query", "")
                limit = arguments.get("limit", 5)
                result = await search(query=query, limit=limit)
                return [mcp_types.TextContent(type="text", text=json.dumps(result))]
            except Exception as e:
                return [mcp_types.TextContent(
                    type="text", 
                    text=json.dumps({"error": str(e)})
                )]
        else:
            return [mcp_types.TextContent(
                type="text", 
                text=json.dumps({"error": f"Tool '{name}' not found"})
            )]
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(),
            ),
        )

if __name__ == "__main__":
    import sys
    import os
    import argparse
    import asyncio
    from pathlib import Path

    # Add project root to Python path to help with imports
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ADK Zendesk Search API")
    parser.add_argument("--mode", choices=["web", "mcp"], default="web",
                      help="Run as web server or MCP server (default: web)")
    args = parser.parse_args()

    if args.mode == "mcp":
        # Run as MCP server
        print("Starting MCP server mode...")
        asyncio.run(run_mcp_server())
    else:
        # Run as web server (default)
        print("Starting Web server mode...")
        run_fastapi()