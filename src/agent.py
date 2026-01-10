import json

from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
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
                # Get LLM response with function calling
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=self._get_system_messages() + self.conversation_history,
                    tool_choice="auto",
                    tools=tool_list,
                    parallel_tool_calls=False,  # issues processing in parallel
                )

                assistant_message = response.choices[0].message

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

                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result
                        })
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        result = {"success": False, "error": str(e)}

                logger.debug(f"Iteration {iteration + 1}: content={assistant_message.content[:1000] if assistant_message.content else '(no content)'}")

                if len(tool_calls) > 0:
                    #TODO: Request more calls to the model
                    return ("incomplete", {"response" : assistant_message.content })

                return ("complete", {"response" : assistant_message.content })

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
    return AgentCard(
        name="Finance Purple Agent",
        description="Purple agent for the finance agentic benchmark",
        url=url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
