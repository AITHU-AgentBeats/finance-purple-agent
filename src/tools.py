"""
Tools connects to the configured MCP server and 
exposes additional tools to finish the iterations.
"""
import asyncio
import json
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
            logger.debug(f"MCP Connection: Already connected to {self.mcp_server_url}")
            return

        # Log MCP connection attempt
        logger.info(f"MCP Connection Request: url={self.mcp_server_url}, context_id={self.context_id}")
        
        try:
            # Create Client
            self._client = Client(self.mcp_server_url)
            await self._client.__aenter__()
            logger.info(f"MCP Connection Response: Successfully connected to {self.mcp_server_url}")
        except Exception as e:
            logger.error(f"MCP Connection Response: Failed to connect to MCP server at {self.mcp_server_url}: {e}")
            raise RuntimeError(f"Cannot connect to MCP server: {e}")

    async def get_tools(self) -> list[dict]:
        """
        List the tools available at the MCP endpoint
        """
        # Log MCP server request attempt
        logger.info(f"MCP Request: method=list_tools, context_id={self.context_id}, url={self.mcp_server_url}")
        
        if not self._client:
            await self.connect()

        tools = await self._client.list_tools()
        if not tools:
            raise RuntimeError("Not connected to MCP server.")

        # Tool schema to OpenAI function
        tool_list = [
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
        
        # Log MCP server response
        logger.info(f"MCP Response: method=list_tools, tools_count={len(tool_list)}")
        logger.info(f"MCP Response Tools: {json.dumps([t['function']['name'] for t in tool_list], indent=2, ensure_ascii=False)}")
        
        return tool_list

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Call tool
        """
        try:
            if not self._client:
                await self.connect()
            # Auto-inject context_id for state isolation
            arguments["context_id"] = self.context_id

            # Log MCP server request
            logger.info(f"MCP Request: tool_name={tool_name}, context_id={self.context_id}")
            logger.info(f"MCP Request Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            logger.debug(f"Calling tool '{tool_name}' with args: {list(arguments.keys())}")
            result = await asyncio.wait_for(
                self._client.call_tool(tool_name, arguments),
                timeout=self._timeout
            )

            # Log the raw result type and attributes for debugging
            logger.debug(f"MCP Response raw type: {type(result)}")
            if hasattr(result, '__dict__'):
                logger.debug(f"MCP Response raw attributes: {list(result.__dict__.keys())}")
            elif isinstance(result, list) and len(result) > 0:
                logger.debug(f"MCP Response is list, first item type: {type(result[0])}")
                if hasattr(result[0], '__dict__'):
                    logger.debug(f"MCP Response first item attributes: {list(result[0].__dict__.keys())}")
            
            # Extract data from result
            # FastMCP CallToolResult can have different attributes: content, text, data, etc.
            response_data = None
            
            # Helper function to extract text from TextContent-like objects
            def extract_text_content(item):
                """Extract and parse text from TextContent objects"""
                if hasattr(item, 'text') and item.text is not None:
                    text = item.text
                    try:
                        # Try to parse as JSON
                        return json.loads(text)
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, return the text as-is
                        return text
                return None
            
            # First check if result is directly a list (some MCP servers return lists directly)
            if isinstance(result, list) and len(result) > 0:
                # Check if it's a list of TextContent objects
                extracted_items = []
                for item in result:
                    parsed_text = extract_text_content(item)
                    if parsed_text is not None:
                        extracted_items.append(parsed_text)
                    elif isinstance(item, (dict, list, str, int, float, bool, type(None))):
                        extracted_items.append(item)
                    else:
                        # Try to extract text or convert to dict
                        if hasattr(item, 'text'):
                            extracted_items.append(item.text)
                        elif hasattr(item, '__dict__'):
                            extracted_items.append(item.__dict__)
                        else:
                            extracted_items.append(str(item))
                response_data = extracted_items[0] if len(extracted_items) == 1 else extracted_items
                logger.debug(f"Result is directly a list: processed {len(extracted_items)} items")
            # Check for common FastMCP result attributes in order of preference
            elif hasattr(result, 'content') and result.content is not None:
                # FastMCP CallToolResult typically has a 'content' attribute
                content = result.content
                logger.debug(f"Extracted content from result.content: type={type(content)}")
                
                # Handle list of TextContent objects
                if isinstance(content, list):
                    extracted_items = []
                    for item in content:
                        parsed_text = extract_text_content(item)
                        if parsed_text is not None:
                            extracted_items.append(parsed_text)
                        elif isinstance(item, (dict, list, str, int, float, bool, type(None))):
                            extracted_items.append(item)
                        else:
                            # Try to extract text or convert to dict
                            if hasattr(item, 'text'):
                                extracted_items.append(item.text)
                            elif hasattr(item, '__dict__'):
                                extracted_items.append(item.__dict__)
                            else:
                                extracted_items.append(str(item))
                    response_data = extracted_items[0] if len(extracted_items) == 1 else extracted_items
                    logger.debug(f"Extracted {len(extracted_items)} items from content list")
                else:
                    response_data = content
            elif hasattr(result, 'text') and result.text is not None:
                # Some MCP tools return 'text' directly
                text = result.text
                try:
                    # Try to parse as JSON
                    response_data = json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    response_data = text
                logger.debug(f"Extracted data from result.text: type={type(response_data)}")
            elif hasattr(result, 'data') and result.data is not None:
                # Some tools return 'data'
                response_data = result.data
                logger.debug(f"Extracted data from result.data: type={type(response_data)}")
            elif isinstance(result, dict):
                # If it's already a dict, use it directly
                response_data = result
                logger.debug(f"Result is already a dict")
            elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                # If it's an async iterable (like async generator), collect results
                logger.info(f"MCP tool '{tool_name}' is async iterable, collecting results...")
                results_list = []
                async for item in result:
                    logger.debug(f"Got item: type={type(item)}")
                    # Try to extract content from each item
                    if hasattr(item, 'text') and item.text is not None:
                        text = item.text
                        try:
                            parsed = json.loads(text)
                            results_list.append(parsed)
                        except (json.JSONDecodeError, TypeError):
                            results_list.append(text)
                    elif hasattr(item, 'content') and item.content is not None:
                        results_list.append(item.content)
                    elif hasattr(item, 'data') and item.data is not None:
                        results_list.append(item.data)
                    elif isinstance(item, (dict, list, str, int, float, bool, type(None))):
                        results_list.append(item)
                    else:
                        # Try to convert to dict if possible
                        try:
                            if hasattr(item, 'text'):
                                results_list.append(item.text)
                            elif hasattr(item, '__dict__'):
                                results_list.append(item.__dict__)
                            else:
                                results_list.append(str(item))
                        except:
                            results_list.append(str(item))
                logger.info(f"MCP tool '{tool_name}' collected {len(results_list)} items from async iterator")
                response_data = results_list[0] if len(results_list) == 1 else results_list
            else:
                # Fallback: try to convert to a usable format
                try:
                    # Try to get dict representation
                    if hasattr(result, '__dict__'):
                        response_data = result.__dict__
                    else:
                        # Last resort: convert to string
                        response_data = {"result": str(result)}
                except Exception as e:
                    logger.warning(f"Could not extract data from result: {e}")
                    response_data = {"result": str(result)}
            
            # Ensure response_data is serializable
            if response_data is None:
                response_data = {"result": "No data returned from tool"}
            
            # Log MCP server response
            logger.info(f"MCP Response: tool_name={tool_name}")
            logger.info(f"MCP Response Data: {json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}")
            
            return response_data

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
