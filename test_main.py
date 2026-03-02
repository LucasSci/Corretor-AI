import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# We mock DB and services before importing app
with patch('app.db.init_db.init_db', new_callable=AsyncMock):
    with patch('app.services.agent.handle_message', new_callable=AsyncMock) as mock_handle_message:
        mock_handle_message.return_value = {"reply": "Mocked response"}
        from app.main import app

client = TestClient(app)

def test_chat_valid_input():
    response = client.post("/chat", json={"contact_id": "user123", "text": "hello"})
    assert response.status_code == 200

def test_chat_invalid_contact_id():
    response = client.post("/chat", json={"contact_id": "a" * 81, "text": "hello"})
    assert response.status_code == 422

def test_chat_invalid_text():
    response = client.post("/chat", json={"contact_id": "user123", "text": "a" * 1001})
    assert response.status_code == 422
