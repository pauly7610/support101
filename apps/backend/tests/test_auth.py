import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_success():
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid():
    response = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401

def test_protected_route():
    login = client.post("/login", data={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "message" in response.json()

def test_protected_route_no_token():
    response = client.get("/protected")
    assert response.status_code == 401

def test_cached_example():
    import time
    t0 = time.time()
    response1 = client.get("/cached-example")
    t1 = time.time()
    response2 = client.get("/cached-example")
    t2 = time.time()
    assert response1.status_code == 200
    assert response2.status_code == 200
    # First response should take longer than second (cached)
    assert (t1-t0) > 1.5
    assert (t2-t1) < 0.5
