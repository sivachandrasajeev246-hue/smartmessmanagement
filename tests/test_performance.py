import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# -----------------------------
# 1️⃣ Basic Load Test (Multiple Requests)
# -----------------------------
def test_multiple_home_requests(client):
    start_time = time.time()

    for _ in range(50):   # simulate 50 requests
        response = client.get("/")
        assert response.status_code == 200

    end_time = time.time()
    total_time = end_time - start_time

    # Basic threshold check (adjust if needed)
    assert total_time < 5   # should complete under 5 seconds


# -----------------------------
# 2️⃣ Attendance Route Performance
# -----------------------------
def test_attendance_route_performance(client):

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "student"

    start_time = time.time()

    for _ in range(20):
        response = client.get("/student/attendance")
        assert response.status_code == 200

    end_time = time.time()
    total_time = end_time - start_time

    assert total_time < 5


# -----------------------------
# 3️⃣ Analytics Route Performance
# -----------------------------
def test_analytics_performance(client):

    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "manager"

    start_time = time.time()

    for _ in range(20):
        response = client.get("/manager/analytics")
        assert response.status_code == 200

    end_time = time.time()
    total_time = end_time - start_time

    assert total_time < 5