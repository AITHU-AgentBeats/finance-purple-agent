import json
import time

from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentCardSignature,
    AgentSkill,
    Part,
    TaskState,
    TextPart,
)

from tools import Tools
from config import logger, log_agent_failure, settings
from openai import OpenAI

# States
TERMINAL_STATES = {
    TaskState.completed,
    TaskState.canceled,
    TaskState.failed,
    TaskState.rejected
}


class PurpleAgent:
    """Basic agent responding finance related questions"""

    def __init__(self, model: str = "moonshotai/Kimi-K2-Instruct", temperature: int = 0, context_id: str = "default"):
        self.model = model
        self.temperature = temperature
        self.context_id = context_id
        self.conversation_history: list[dict] = []
        self._tools = None
        if settings.MCP_ENABLED:
            self._tools = Tools(settings.MCP_SERVER, context_id=context_id)
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=settings.NEBIUS_API_KEY
        )


    async def process_message(
        self,
        message: str,
        reset_conversation: bool = False,
        updater: 'TaskUpdater | None' = None
    ) -> tuple[str, dict]:
        """
        Process a message by looping internally with LLM and MCP tools.

        Args:
            message: User message to process
            reset_conversation: Start from scratch
            updater: Optional TaskUpdater for sending A2A progress updates

        Returns:
            tuple: (Status, Response)
        """

        if reset_conversation:
            self.conversation_history = []

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # Get available tools (each time)
        tool_list = await self._tools.get_tools() if self._tools else None

        # Loop until final answer is obtained (just for errors)
        for iteration in range(settings.MAX_ITERATIONS):
            try:
                # Prepare messages for LLM call
                messages = self._get_system_messages() + self.conversation_history

                # Log LLM request
                logger.info(f"LLM Request [iteration {iteration + 1}]: model={self.model}, temperature={self.temperature}, context_id={self.context_id}")
                logger.info(f"LLM Request [iteration {iteration + 1}]: {len(messages)} messages in conversation")
                
                # Log full request text/messages
                logger.info(f"LLM Request Messages [iteration {iteration + 1}]:")
                for idx, msg in enumerate(messages):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if role == "system":
                        logger.info(f"  Message {idx + 1} [{role}]: {content[:500]}{'...' if len(content) > 500 else ''}")
                    elif role == "user":
                        logger.info(f"  Message {idx + 1} [{role}]: {content}")
                    elif role == "assistant":
                        logger.info(f"  Message {idx + 1} [{role}]: {content[:500]}{'...' if len(content) > 500 else ''}")
                    elif role == "tool":
                        tool_name = msg.get("name", "unknown")
                        tool_content = msg.get("content", "")
                        logger.info(f"  Message {idx + 1} [{role}:{tool_name}]: {tool_content[:500]}{'...' if len(tool_content) > 500 else ''}")
                    else:
                        logger.info(f"  Message {idx + 1} [{role}]: {str(msg)[:500]}")
                
                logger.debug(f"LLM Request full messages JSON: {json.dumps(messages, indent=2, ensure_ascii=False)}")
                
                # Log tools being passed to LLM
                if self._tools:
                    logger.info(f"LLM Request Tools [iteration {iteration + 1}]: {len(tool_list)} tool(s) available")
                    logger.info(f"LLM Request Tool Names: {[t['function']['name'] for t in tool_list]}")
                else:
                    logger.info(f"LLM Request Tools [iteration {iteration + 1}]: no tools available")
                
                logger.debug(f"LLM Request messages: {len(messages)} messages, last user message: {self.conversation_history[-1]['content'][:200] if self.conversation_history else 'N/A'}")

                # Get LLM response with function calling
                start_time = time.time()
                if self._tools:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        temperature=self.temperature,
                        messages=messages,
                        tools=tool_list if tool_list else None,
                        tool_choice="auto",  # Enable automatic tool calling
                        #parallel_tool_calls=False,  # Process one tool at a time
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        temperature=self.temperature,
                        messages=messages
                    )
                elapsed_time = time.time() - start_time

                assistant_message = response.choices[0].message
                
                # Log LLM response
                response_content = assistant_message.content or ""
                response_length = len(response_content) if response_content else 0
                logger.info(f"LLM Response [iteration {iteration + 1}]: elapsed_time={elapsed_time:.2f}s, response_length={response_length} chars")
                
                # Log full response text
                if response_content:
                    logger.info(f"LLM Response Text [iteration {iteration + 1}]:")
                    logger.info(f"  {response_content}")
                else:
                    logger.info(f"LLM Response Text [iteration {iteration + 1}]: (no content)")
                
                # Log tool calls if present
                tool_calls = assistant_message.tool_calls
                if tool_calls:
                    logger.info(f"LLM Response Tool Calls [iteration {iteration + 1}]: {len(tool_calls)} tool call(s)")
                    for idx, tool_call in enumerate(tool_calls):
                        tool_name = tool_call.function.name
                        tool_args = tool_call.function.arguments
                        logger.info(f"  Tool Call {idx + 1}: {tool_name}")
                        logger.info(f"    Arguments: {tool_args}")
                else:
                    logger.info(f"LLM Response Tool Calls [iteration {iteration + 1}]: none")

                # Log token usage if available
                if hasattr(response, 'usage') and response.usage:
                    usage = response.usage
                    logger.info(f"LLM Token Usage [iteration {iteration + 1}]: prompt_tokens={getattr(usage, 'prompt_tokens', 'N/A')}, completion_tokens={getattr(usage, 'completion_tokens', 'N/A')}, total_tokens={getattr(usage, 'total_tokens', 'N/A')}")
                
                # Log full response object at DEBUG level
                logger.debug(f"LLM Response full object: {json.dumps({'content': response_content, 'tool_calls': [{'name': tc.function.name, 'arguments': tc.function.arguments} for tc in (tool_calls or [])]}, indent=2, ensure_ascii=False)}")

                # Add response to history
                message_dict = {
                    "role": "assistant",
                    "content": assistant_message.content
                }

                self.conversation_history.append(message_dict)

                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    if "context_id" in tool_args:
                        del tool_args["context_id"] # Causes issues
                    logger.info(f"Calling tool {tool_name} with args {tool_args}")

                    try:
                        result = await self._tools.call_tool(tool_name, tool_args)
                        logger.info(f"Tool {tool_name} result {result}")

                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(result)
                        })
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        result = {"success": False, "error": str(e)}

                logger.debug(f"Iteration {iteration + 1}: content={response_content[:1000] if response_content else '(no content)'}")

                # If there are no tool calls, the LLM gave a final answer - return it
                if not tool_calls:
                    return "Final answer", {"status" : "complete", "response" : assistant_message.content}
                
                # If there are tool calls, continue to next iteration so LLM can use the tool results
                # The loop will continue and call LLM again with the tool results in conversation_history

            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")
                log_agent_failure(
                    "iteration error",
                    user_message=message,
                    context_id=self.context_id,
                    detail=str(e),
                )

        # Max iterations reached without submit_answer
        logger.warning(f"Max iterations ({settings.MAX_ITERATIONS}) reached without submitting answer")
        log_agent_failure(
            "max iterations reached without final answer",
            user_message=message,
            context_id=self.context_id,
            detail=f"MAX_ITERATIONS={settings.MAX_ITERATIONS}",
        )

    def _get_system_messages(self) -> list[dict]:
        """Get system messages for the agent."""
        default_message = """
                You are a financial assistant providing faithful information regarding the questions posed by the user.
            """
        if self._tools:
            default_message += "Use tools to complete your knowledge."

        return [{
            "role": "system",
            "content": default_message
        }]

def create_agent_card(url: str) -> AgentCard:
    """Create the agent card for the finance agent."""
    skill = AgentSkill(
        id="expertise",
        name="Financial expertise",
        description="Responds to financial questions",
        tags=["finance", "purple"],
        examples=[
            "What was Apple's revenue in Q4 2024?",
            "Who is the CFO of Microsoft?",
        ],
    )
    
    # Standard A2A protocol JSON-RPC method signatures
    # The A2A SDK's DefaultRequestHandler automatically exposes these standard methods:
    # - message/send: Send a message and wait for completion
    # - message/stream: Send a message and receive streaming updates
    # - tasks/get: Get task status by ID
    # - tasks/cancel: Cancel a task
    signatures = [
        AgentCardSignature(
            protected="false",
            signature="message/send"
        ),
        AgentCardSignature(
            protected="false",
            signature="message/stream"
        ),
        AgentCardSignature(
            protected="false",
            signature="tasks/get"
        ),
        AgentCardSignature(
            protected="false",
            signature="tasks/cancel"
        )
    ]
    
    return AgentCard(
        name="Finance Purple Agent",
        description="Purple agent for the finance agentic benchmark",
        url=url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        signatures=signatures,
    )
