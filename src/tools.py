"""
Tools connects to the configured MCP server and 
exposes additional tools to finish the iterations.
"""
import asyncio
from typing import Optional

from fastmcp import Client
from config import logger, settings


class Tools:
    def __init__(self, mcp_server: Optional[str] = None, context_id: Optional[str] = None):
        """
        Initialize the tools available
        """
        self.mcp_server_url = mcp_server or settings.MCP_SERVER
        if not self.mcp_server_url.endswith("/mcp"):
            self.mcp_server_url += "/mcp"
        self._client = None
        self._tools = None
        self.context_id = context_id or "default"
        self._timeout = 60

    async def connect(self):
        """Connect"""
        if self._client:
            return

        try:
            # Create Client
            self._client = Client(self.mcp_server_url)
            await self._client.__aenter__()
        except Exception as e:
            logger.error(f"Failed to connect to MCP server at {self.mcp_server_url}: {e}")
            raise RuntimeError(f"Cannot connect to MCP server: {e}")

    async def get_tools(self) -> list[dict]:
        """
        List the tools available at the MCP endpoint
        """
        if not self._client:
            await self.connect()

        tools = await self._client.list_tools()
        if not tools:
            raise RuntimeError("Not connected to MCP server.")

        # Tool schema to OpenAI function
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Call tool
        """
        try:
            if not self._client:
                await self.connect()
            # Auto-inject context_id for state isolation
            arguments["context_id"] = self.context_id

            logger.debug(f"Calling tool '{tool_name}' with args: {list(arguments.keys())}")
            result = await asyncio.wait_for(
                self._client.call_tool(tool_name, arguments),
                timeout=self._timeout
            )

            # Extract data from result
            # FastMCP returns different formats depending on the tool
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes, dict)):
                # If it's an iterable (like async generator), collect results
                logger.info(f"MCP tool '{tool_name}' is async iterable, collecting results...")
                results = []
                async for item in result:
                    logger.debug(f"Got item: type={type(item)}, has_data={hasattr(item, 'data')}")
                    if hasattr(item, 'data'):
                        results.append(item.data)
                    else:
                        results.append(item)
                logger.info(f"MCP tool '{tool_name}' collected {len(results)} items from async iterator")
                return {"success": True, "result": results[0] if len(results) == 1 else results}
            elif hasattr(result, 'data'):
                return result.data
            elif isinstance(result, dict):
                return result
            else:
                return {"result": str(result)}

        except asyncio.TimeoutError:
            timeout_val = 120.0 if tool_name == "submit_answer" else 60.0
            logger.error(f"Tool '{tool_name}' timed out after {timeout_val}s (client-side hang)")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' timed out"
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return {
                "success": False,
                "error": f"MCP tool call failed: {error_msg}"
            }
