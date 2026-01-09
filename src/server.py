import os
import argparse

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from agent import create_agent_card
from executor import PurpleAgentExecutor
from config import logger, settings


def main():
    parser = argparse.ArgumentParser(description="Run the Finance Agent Baseline.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9019, help="Port to bind")
    parser.add_argument("--card-url", type=str, help="External URL for agent card")
    args = parser.parse_args()

    agent_url = args.card_url or f"http://{args.host}:{args.port}/"

    agent_card = create_agent_card(agent_url)

    request_handler = DefaultRequestHandler(
        agent_executor=PurpleAgentExecutor(model=settings.MODEL_NAME),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logger.info(f"Starting Finance Purple Agent on {args.host}:{args.port}")

    uvicorn.run(server.build(), host=args.host, port=args.port)

if __name__ == "__main__":
    main()
