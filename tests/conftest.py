"""Pytest configuration and fixtures."""
import os
import pytest
import httpx


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--agent-url",
        action="store",
        default="http://127.0.0.1:9019",
        help="Base URL of the agent server",
    )


@pytest.fixture(scope="session")
def agent_url(pytestconfig):
    """Get the agent URL from command line option or environment variable."""
    url = pytestconfig.getoption("--agent-url")
    if not url:
        url = os.getenv("AGENT_URL", "http://127.0.0.1:9019")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def client(agent_url):
    """Create an HTTP client for making requests to the agent."""
    return httpx.Client(base_url=agent_url, timeout=30.0)


@pytest.fixture(scope="session")
def agent_card(client):
    """Fetch and return the agent card."""
    response = client.get("/card")
    response.raise_for_status()
    return response.json()
