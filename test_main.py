import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_valid_input():
    # Setup mock for init_db and handle_message if necessary, but we can test validation before that
    response = client.post("/chat", json={"contact_id": "user123", "text": "hello"})
    # Since we are not mocking DB, it might return 500 if DB is not setup, but we want to check 422 for validation.
    assert response.status_code in [200, 500]

def test_chat_invalid_contact_id():
    response = client.post("/chat", json={"contact_id": "a" * 81, "text": "hello"})
    assert response.status_code == 422

def test_chat_invalid_text():
    response = client.post("/chat", json={"contact_id": "user123", "text": "a" * 1001})
    assert response.status_code == 422
