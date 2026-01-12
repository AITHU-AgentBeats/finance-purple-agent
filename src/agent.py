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
from config import logger, settings
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
        tool_list = await self._tools.get_tools()

        # Loop until final answer is obtained (just for errors)
        for iteration in range(settings.MAX_ITERATIONS):
            try:
                # Prepare messages for LLM call
                messages = self._get_system_messages() + self.conversation_history
                
                # Log LLM request
                logger.info(f"LLM Request [iteration {iteration + 1}]: model={self.model}, temperature={self.temperature}, context_id={self.context_id}")
                logger.debug(f"LLM Request messages: {len(messages)} messages, last user message: {self.conversation_history[-1]['content'][:200] if self.conversation_history else 'N/A'}")
                
                # Get LLM response with function calling
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=messages,
                    #tool_choice="auto",
                    #parallel_tool_calls=False,  # Process one tool at a time
                )
                elapsed_time = time.time() - start_time

                assistant_message = response.choices[0].message
                
                # Log LLM response
                response_content = assistant_message.content or ""
                response_length = len(response_content) if response_content else 0
                logger.info(f"LLM Response [iteration {iteration + 1}]: elapsed_time={elapsed_time:.2f}s, response_length={response_length} chars")
                logger.debug(f"LLM Response content: {response_content[:500] if response_content else '(no content)'}")
                
                # Log token usage if available
                if hasattr(response, 'usage') and response.usage:
                    usage = response.usage
                    logger.info(f"LLM Token Usage [iteration {iteration + 1}]: prompt_tokens={getattr(usage, 'prompt_tokens', 'N/A')}, completion_tokens={getattr(usage, 'completion_tokens', 'N/A')}, total_tokens={getattr(usage, 'total_tokens', 'N/A')}")

                # Add response to history
                message_dict = {
                    "role": "assistant",
                    "content": assistant_message.content
                }

                self.conversation_history.append(message_dict)
                tool_calls = assistant_message.tool_calls
                logger.info(f"Calling tools {tool_calls}")

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

                return "Final answer", {"status" : "complete", "response" : assistant_message.content}

            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")

        # Max iterations reached without submit_answer
        logger.warning(f"Max iterations ({settings.MAX_ITERATIONS}) reached without submitting answer")

    def _get_system_messages(self) -> list[dict]:
        """Get system messages for the agent."""
        return [{
            "role": "system",
            "content": """
                You are a financial assistant providing faithful information regarding the questions posed by the user.
                Use tools to complete your knowledge.
            """
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
