import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def get_token():
    username = "protecteduser"
    password = "protectedpass"
    # Register the user
    client.post("/register", data={"username": username, "password": password})
    # Login to get token
    r = client.post("/login", data={"username": username, "password": password})
    return r.json()["access_token"]

def test_protected_endpoint():
    token = get_token()
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "message" in r.json()

def test_protected_endpoint_no_token():
    r = client.get("/protected")
    assert r.status_code == 401

def test_cached_example():
    import time
    t0 = time.time()
    r1 = client.get("/cached-example")
    t1 = time.time()
    r2 = client.get("/cached-example")
    t2 = time.time()
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert (t1-t0) > 1.5  # First call is slow
    assert (t2-t1) < 0.5  # Second call is fast (cached)

def test_ingest_documentation_requires_auth():
    # Try without token
    with open("README.md", "rb") as f:
        r = client.post("/ingest_documentation", files={"file": ("README.md", f)}, data={"chunk_size": 1000})
        assert r.status_code == 401
    # Try with token
    token = get_token()
    with open("README.md", "rb") as f:
        r = client.post("/ingest_documentation", files={"file": ("README.md", f)}, data={"chunk_size": 1000}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (200, 400)  # 400 if file type is not allowed
