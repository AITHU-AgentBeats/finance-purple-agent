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

## Running with Docker

The project includes a Dockerfile for containerized deployment.

### Prerequisites

- [Docker](https://www.docker.com/) installed and running

### Building the Docker Image

Build the Docker image from the project root:

```bash
docker build -t finance-purple-agent .
```

This will:
- Use the official `uv` Python image as the base
- Install all dependencies using `uv sync --locked`
- Configure the container to run the server on port 9019

### Running the Container

Run the container with port mapping:

```bash
docker run -d -p 9019:9019 --name finance-purple-agent finance-purple-agent
```

### Environment Variables

To pass environment variables (like `NEBIUS_API_KEY`) to the container:

```bash
docker run -d -p 9019:9019 \
  -e NEBIUS_API_KEY=your_api_key_here \
  -e MODEL_NAME=moonshotai/Kimi-K2-Instruct \
  --name finance-purple-agent \
  finance-purple-agent
```

### Using Environment File

You can also use a `.env` file:

```bash
docker run -d -p 9019:9019 \
  --env-file .env \
  --name finance-purple-agent \
  finance-purple-agent
```


## Testing the Server

Once the server is running, you can test it by accessing the agent card endpoint:

### Using curl

```bash
curl http://127.0.0.1:9019/card
```



### Example Response

The endpoint returns a JSON object containing the agent's metadata, including:
- `name`: "Finance Purple Agent"
- `version`: "0.1.0"
- `description`: Agent description
- `capabilities`: Agent capabilities (e.g., streaming)
- `skills`: List of agent skills with examples
- `url`: Agent service URL
- `signatures`: List of available JSON-RPC methods

## Sending Queries to the Agent

The agent supports the A2A protocol and exposes JSON-RPC 2.0 methods for sending queries. The main method for sending queries is `message/send`.

### Using curl

Send a query using the `message/send` method:

```bash
curl -X POST http://127.0.0.1:9019/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "unique-message-id",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "What was Apple revenue in Q4 2024?"
          }
        ]
      }
    },
    "id": 1
  }'
```

### Request Format

The request follows JSON-RPC 2.0 format:

- **Endpoint**: `POST http://127.0.0.1:9019/`
- **Method**: `"message/send"`
- **Message Structure**:
  - `messageId`: Unique identifier for the message
  - `role`: Message role (typically `"user"` for queries)
  - `parts`: Array of message parts, each containing:
    - `kind`: Part type (`"text"` for text messages)
    - `text`: The actual query text

### Example Query

```bash
curl -X POST http://127.0.0.1:9019/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "query-1",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Who is the CFO of Microsoft?"
          }
        ]
      }
    },
    "id": 1
  }' | python -m json.tool
```

### Example Response

```json
{
    "id": 1,
    "jsonrpc": "2.0",
    "result": {
        "artifacts": [
            {
                "artifactId": "unique-artifact-id",
                "name": "Response",
                "parts": [
                    {
                        "kind": "text",
                        "text": "complete"
                    },
                    {
                        "data": {
                            "response": "The CFO of Microsoft is Amy Hood."
                        },
                        "kind": "data"
                    }
                ]
            }
        ],
        "contextId": "unique-context-id",
        "history": [...],
        "id": "task-id",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2026-01-12T00:49:42.026112+00:00"
        }
    }
}
```

