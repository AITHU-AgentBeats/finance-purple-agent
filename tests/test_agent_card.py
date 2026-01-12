"""Tests for the agent card endpoint."""
import pytest


def test_agent_card_endpoint_exists(client):
    """Test that the /card endpoint exists and returns 200."""
    response = client.get("/card")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_agent_card_structure(agent_card):
    """Test that the agent card has the required structure."""
    assert "name" in agent_card
    assert "version" in agent_card
    assert "description" in agent_card
    assert "url" in agent_card
    assert "capabilities" in agent_card
    assert "skills" in agent_card
    assert "signatures" in agent_card


def test_agent_card_content(agent_card):
    """Test that the agent card contains expected content."""
    assert agent_card["name"] == "Finance Purple Agent"
    assert agent_card["version"] == "0.1.0"
    assert "finance" in agent_card["description"].lower() or "purple" in agent_card["description"].lower()
    assert isinstance(agent_card["skills"], list)
    assert len(agent_card["skills"]) > 0


def test_agent_card_skills(agent_card):
    """Test that the agent card has valid skills."""
    skills = agent_card["skills"]
    assert len(skills) > 0
    
    # Check first skill structure
    skill = skills[0]
    assert "id" in skill
    assert "name" in skill
    assert "description" in skill
    assert "tags" in skill
    assert "examples" in skill
    
    # Check that finance-related tags exist
    assert any("finance" in tag.lower() for tag in skill["tags"])


def test_agent_card_signatures(agent_card):
    """Test that the agent card has required method signatures."""
    signatures = agent_card["signatures"]
    assert isinstance(signatures, list)
    assert len(signatures) > 0
    
    # Extract signature strings
    signature_strings = [sig.get("signature", "") for sig in signatures]
    
    # Check for required A2A protocol methods
    assert "message/send" in signature_strings
    assert "message/stream" in signature_strings
    assert "tasks/get" in signature_strings
    assert "tasks/cancel" in signature_strings


def test_agent_card_capabilities(agent_card):
    """Test that the agent card has valid capabilities."""
    capabilities = agent_card["capabilities"]
    assert isinstance(capabilities, dict)
    # Streaming capability should be present
    assert "streaming" in capabilities
    assert capabilities["streaming"] is True
