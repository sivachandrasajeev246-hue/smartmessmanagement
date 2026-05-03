import pytest
from app import app
import sqlite3


# ------------------------------
# TEST CLIENT FIXTURE
# ------------------------------
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client


# ------------------------------
# TEST 1: Student Login Success
# ------------------------------
def test_student_login_success(client):
    response = client.post(
        "/",
        data={
            "email": "student1@test.com",
            "password": "123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Student Panel" in response.data


# ------------------------------
# TEST 2: Manager Login Success
# ------------------------------
def test_manager_login_success(client):
    response = client.post(
        "/",
        data={
            "email": "manager@test.com",
            "password": "123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Manager Panel" in response.data


# ------------------------------
# TEST 3: Admin Login Success
# ------------------------------
def test_admin_login_success(client):
    response = client.post(
        "/",
        data={
            "email": "admin@test.com",
            "password": "123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Admin Panel" in response.data


# ------------------------------
# TEST 4: Invalid Login
# ------------------------------
def test_invalid_login(client):
    response = client.post(
        "/",
        data={
            "email": "wrong@test.com",
            "password": "wrong"
        },
        follow_redirects=True
    )

    assert b"Invalid credentials" in response.data


# ------------------------------
# TEST 5: Unauthorized Access
# ------------------------------
def test_unauthorized_manager_access(client):
    # Try accessing manager dashboard without login
    response = client.get("/manager", follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data