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


def test_attendance_mark_breakfast(client):
    # Simulate student login session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "student"

    response = client.get("/student/attendance/process/breakfast")

    assert response.status_code == 200
    assert b"attendance" in response.data.lower()