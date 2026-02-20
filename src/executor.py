from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    Task,
    TextPart,
    UnsupportedOperationError,
    InvalidRequestError,
)
from a2a.utils import new_agent_text_message, new_task, get_message_text
from a2a.utils.errors import ServerError

from agent import PurpleAgent, TERMINAL_STATES
from config import logger, log_agent_failure, log_agent_success

class PurpleAgentExecutor(AgentExecutor):
    """Executor that wraps the FinanceAgent for A2A protocol."""

    def __init__(self, model: str = "openai/gpt-4o-mini", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self.agents: dict[str, PurpleAgent] = {}

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        msg = context.message
        if not msg:
            raise ServerError(error=InvalidRequestError(message="Missing message in request"))

        task = context.current_task
        if task and task.status.state in TERMINAL_STATES:
            raise ServerError(
                error=InvalidRequestError(
                    message=f"Task {task.id} already processed (state: {task.status.state})"
                )
            )

        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)

        context_id = task.context_id
        agent = self.agents.get(context_id)
        if not agent:
            agent = PurpleAgent(
                model=self.model,
                temperature=self.temperature,
                context_id=context_id  # Pass context_id for MCP state isolation
            )
            self.agents[context_id] = agent

        # Check if this is a new conversation
        is_new = len(agent.conversation_history) == 0
        message_text = get_message_text(msg)

        updater = TaskUpdater(event_queue, task.id, context_id)
        await updater.start_work()

        try:
            status_message, answer_data = await agent.process_message(
                message_text,
                reset_conversation=is_new,
                updater=updater  # Pass updater for A2A progress updates
            )

            # Create parts for the artifact
            parts = [Part(root=TextPart(text=status_message))]

            # If we have structured answer data, include it as DataPart
            if answer_data:
                parts.append(Part(root=DataPart(data=answer_data)))

            await updater.add_artifact(
                parts=parts,
                name="Response",
            )
            await updater.complete()

            response_preview = (answer_data or {}).get("response", "") if isinstance(answer_data, dict) else ""
            log_agent_success(
                user_message=message_text,
                context_id=context_id,
                task_id=task.id,
                response_preview=response_preview or status_message,
            )

        except Exception as e:
            logger.error(f"Agent error: {e}")
            log_agent_failure(
                "executor exception",
                user_message=message_text,
                context_id=context_id,
                task_id=task.id,
                detail=str(e),
            )
            await updater.failed(
                new_agent_text_message(f"Error: {e}", context_id=context_id, task_id=task.id)
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
