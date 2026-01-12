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

        # Loop until submit_answer is called
        for iteration in range(settings.MAX_ITERATIONS):
            try:
                # Get LLM response with function calling
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=self._get_system_messages() + self.conversation_history,
                    #tool_choice="auto",
                    #parallel_tool_calls=False,  # Process one tool at a time
                )

                assistant_message = response.choices[0].message

                # Add assistant response to history (use model_dump() to preserve exact format)
                message_dict = {
                    "role": "assistant",
                    "content": assistant_message.content
                }

                self.conversation_history.append(message_dict)

                logger.debug(f"Iteration {iteration + 1}: content={assistant_message.content[:1000] if assistant_message.content else '(no content)'}")

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
