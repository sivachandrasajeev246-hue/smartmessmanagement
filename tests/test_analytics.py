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


def test_manager_analytics_access(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 2  # manager id
        sess["role"] = "manager"

    response = client.get("/manager/analytics")

    assert response.status_code == 200
    assert b"Analytics" in response.data


def test_manager_export_csv(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "manager"

    response = client.get("/manager/export")

    assert response.status_code == 200
    assert "text/csv" in response.content_type