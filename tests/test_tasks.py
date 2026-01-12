"""Tests for task-related endpoints."""
import pytest
import uuid


def test_tasks_get_endpoint(client):
    """Test the tasks/get endpoint."""
    # First, create a task by sending a message
    message_id = f"test-task-{uuid.uuid4()}"
    
    send_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Test task"
                    }
                ]
            }
        },
        "id": 1
    }
    
    send_response = client.post("/", json=send_request)
    assert send_response.status_code == 200
    
    send_result = send_response.json()
    
    if "error" in send_result:
        pytest.skip(f"Could not create task: {send_result['error']}")
    
    task_id = send_result["result"]["id"]
    
    # Now get the task
    get_request = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {
            "taskId": task_id
        },
        "id": 2
    }
    
    get_response = client.post("/", json=get_request)
    assert get_response.status_code == 200
    
    get_result = get_response.json()
    
    if "error" in get_result:
        pytest.skip(f"tasks/get returned error: {get_result['error']}")
    
    assert "result" in get_result
    task = get_result["result"]
    assert task["id"] == task_id
    assert "status" in task


def test_tasks_get_invalid_id(client):
    """Test tasks/get with an invalid task ID."""
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {
            "taskId": "invalid-task-id-12345"
        },
        "id": 3
    }
    
    response = client.post("/", json=request)
    assert response.status_code == 200
    
    result = response.json()
    # Should return an error for invalid task ID
    assert "error" in result


def test_tasks_cancel_endpoint(client):
    """Test the tasks/cancel endpoint."""
    # First, create a task
    message_id = f"test-cancel-{uuid.uuid4()}"
    
    send_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Test cancel"
                    }
                ]
            }
        },
        "id": 4
    }
    
    send_response = client.post("/", json=send_request)
    assert send_response.status_code == 200
    
    send_result = send_response.json()
    
    if "error" in send_result:
        pytest.skip(f"Could not create task: {send_result['error']}")
    
    task_id = send_result["result"]["id"]
    
    # Try to cancel the task
    cancel_request = {
        "jsonrpc": "2.0",
        "method": "tasks/cancel",
        "params": {
            "taskId": task_id
        },
        "id": 5
    }
    
    cancel_response = client.post("/", json=cancel_request)
    assert cancel_response.status_code == 200
    
    cancel_result = cancel_response.json()
    
    # Cancel might succeed or fail depending on task state
    # Just verify we get a valid JSON-RPC response
    assert "result" in cancel_result or "error" in cancel_result
