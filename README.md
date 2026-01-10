# Finance Purple Agent

Purple agent to be used as baseline for the finance benchmark. It uses NEBIUS by default to instantiate the selected LLM.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd finance-purple-agent
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

   This will:
   - Create a virtual environment at `.venv`
   - Install all required dependencies from `pyproject.toml`
   - Install development dependencies (pytest, ruff)

## Configuration

The server requires environment variables for configuration. Create a `.env` file in the project root:

```bash
# Required: NEBIUS API Key
NEBIUS_API_KEY=your_nebius_api_key_here

# Optional: Model configuration (defaults shown)
MODEL_PROVIDER=nebius
MODEL_NAME=moonshotai/Kimi-K2-Instruct

# Optional: MCP Server URL
MCP_SERVER=http://127.0.0.1:9020

# Optional: Log level
LOG_LEVEL=INFO
```

## Running the Server

Start the server using `uv run`:

```bash
uv run python src/server.py
```

The server will start on `http://127.0.0.1:9019` by default.

### Server Options

You can customize the server host, port, and card URL:

```bash
uv run python src/server.py --host 0.0.0.0 --port 8080 --card-url http://example.com
```

Options:
- `--host`: Host to bind (default: `127.0.0.1`)
- `--port`: Port to bind (default: `9019`)
- `--card-url`: External URL for agent card (default: `http://{host}:{port}/`)

## Development

To run with development dependencies:

```bash
uv sync --dev
```

Run tests:
```bash
uv run pytest
```

Run linting:
```bash
uv run ruff check .
```
