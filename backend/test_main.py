import sys
import pytest
from fastapi.testclient import TestClient

# Reconfigure stdout/stderr to utf-8 for Windows test runners
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from main import app

# Initialize FastAPI test client
client = TestClient(app)


def test_health_check():
    """Verify that the /health GET endpoint returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint():
    """Verify that the /chat POST endpoint returns 200, an answer, and sources list."""
    payload = {"question": "What is this college about?"}
    response = client.post("/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert response schema contains answer and sources
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"].strip()) > 0
    assert isinstance(data["sources"], list)
