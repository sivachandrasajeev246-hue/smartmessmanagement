import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
def test_full_student_flow(client):
    # Login
    response = client.post("/", data={
        "email": "student1@test.com",
        "password": "123"
    }, follow_redirects=True)

    assert response.status_code == 200

    # Now session exists
    response = client.get("/student")
    assert response.status_code == 200

