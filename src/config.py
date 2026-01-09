import os
import json
from dataclasses import dataclass

from dotenv import load_dotenv, find_dotenv
from loguru import logger as _logger

# Load .env once when this module is imported
load_dotenv(find_dotenv(), override=True)


@dataclass(frozen=True)
class Settings:
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY")
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "nebius")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "moonshotai/Kimi-K2-Instruct")

    # Tools
    MCP_SERVER: str = os.getenv("MCP_SERVER", "http://127.0.0.1:9020")

    # Finish condition
    MAX_ITERATIONS = 20


# Create settings
settings = Settings()

def configure_logger():
    """
    Configure logger to be used
    """
    # idempotent config: remove existing handlers and add one handler
    _logger.remove()
    _logger.add(
        lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
    )


# configure logger on import so other modules can `from .config import logger`
configure_logger()
logger = _logger