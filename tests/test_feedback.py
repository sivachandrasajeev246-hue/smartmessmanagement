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


def test_feedback_submission(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "student"

    # Fake feedback submission (dish_id 1 assumed exists)
    response = client.post(
        "/student/feedback",
        data={
            "rating_1": "5"
        },
        follow_redirects=True
    )

    assert response.status_code == 200