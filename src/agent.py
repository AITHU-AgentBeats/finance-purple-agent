import litellm

from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Part,
    TaskState,
    TextPart,
)

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

    def __init__(self, model: str = "moonshotai/Kimi-K2-Instruct", context_id: str = "default"):
        self.model = model
        self.context_id = context_id
        self.conversation_history: list[dict] = []
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=settings.NEBIUS_API_KEY
        )


    async def process_message(
        self,
        message: str,
        new_conversation: bool = False,
        updater: 'TaskUpdater | None' = None
    ) -> tuple[str, dict | None]:
        """
        Process a message by looping internally with LLM and MCP tools.

        Args:
            message: User message to process
            new_conversation: Whether this starts a new conversation
            updater: Optional TaskUpdater for sending A2A progress updates

        Returns:
            tuple: (status, response)
        """

        if new_conversation:
            self.conversation_history = []

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # Loop until submit_answer is called
        for iteration in range(settings.MAX_ITERATIONS):
            try:
                # Get LLM response with function calling (tools from MCP server)
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self._get_system_messages() + self.conversation_history,
                    tool_choice="auto",
                    parallel_tool_calls=False,  # Process one tool at a time
                )

                assistant_message = response.choices[0].message

                # Add assistant response to history (use model_dump() to preserve exact format)
                message_dict = {
                    "role": "assistant",
                    "content": assistant_message.content
                }

                # Add tool_calls if present
                if assistant_message.tool_calls:
                    message_dict["tool_calls"] = [
                        tc.model_dump() if hasattr(tc, 'model_dump') else tc
                        for tc in assistant_message.tool_calls
                    ]

                self.conversation_history.append(message_dict)

                logger.debug(f"Iteration {iteration + 1}: content={assistant_message.content[:100] if assistant_message.content else '(no content)'}, tool_calls={len(tool_calls) if tool_calls else 0}")

                self.conversation_history.append({
                    "role": "user",
                    "content": "Please use one of the available tools to continue your research, or call submit_answer if you're ready."
                })

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
                Use tools when available to expand your knowledge.
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
