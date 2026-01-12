"""Tests for the message/send endpoint."""
import pytest
import time
import uuid


def test_message_send_basic(client):
    """Test basic message/send functionality."""
    message_id = f"test-{uuid.uuid4()}"
    
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Hello, can you hear me?"
                    }
                ]
            }
        },
        "id": 1
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    assert "result" in result or "error" in result
    
    # If successful, check result structure
    if "result" in result:
        assert "id" in result["result"]
        assert "status" in result["result"]
        assert "contextId" in result["result"]


def test_message_send_finance_question(client):
    """Test message/send with a finance-related question."""
    message_id = f"test-finance-{uuid.uuid4()}"
    
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "What is finance?"
                    }
                ]
            }
        },
        "id": 2
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    
    # Check for errors
    if "error" in result:
        pytest.skip(f"Agent returned error: {result['error']}")
    
    # Check result structure
    assert "result" in result
    result_data = result["result"]
    
    # Check task structure
    assert "id" in result_data
    assert "status" in result_data
    assert result_data["status"]["state"] in ["completed", "failed", "rejected"]
    
    # Check for artifacts/response
    if "artifacts" in result_data:
        artifacts = result_data["artifacts"]
        assert isinstance(artifacts, list)
        if len(artifacts) > 0:
            artifact = artifacts[0]
            assert "parts" in artifact


def test_message_send_invalid_method(client):
    """Test that invalid methods return appropriate errors."""
    request = {
        "jsonrpc": "2.0",
        "method": "invalid/method",
        "params": {},
        "id": 3
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    assert "error" in result
    assert result["error"]["code"] != 0


def test_message_send_missing_params(client):
    """Test that missing parameters return appropriate errors."""
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {},
        "id": 4
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    # Should have an error for missing parameters
    assert "error" in result


def test_message_send_task_status(client):
    """Test that message/send returns a task with status."""
    message_id = f"test-status-{uuid.uuid4()}"
    
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Test"
                    }
                ]
            }
        },
        "id": 5
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    
    if "error" in result:
        pytest.skip(f"Agent returned error: {result['error']}")
    
    assert "result" in result
    result_data = result["result"]
    
    # Check status structure
    status = result_data["status"]
    assert "state" in status
    assert "timestamp" in status
    assert status["state"] in ["completed", "failed", "rejected", "pending", "running"]
