# [C5-REAL] Exergy-Maximized
import pytest
from fastapi.testclient import TestClient
import jwt
from cortex.api.analysis import app, JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "C5-REAL"
    assert resp.json()["engine"] == "MOSKV-1 OMEGA"

def test_entropy_endpoint():
    resp = client.get("/entropy?payload=test_structural_noir_entropy_calculation")
    assert resp.status_code == 200
    assert "entropy" in resp.json()
    assert resp.json()["classification"] in ["LOW_EXERGY", "STRUCTURAL_NOIR"]

def test_facts_endpoint_missing_auth():
    resp = client.get("/facts?query=all")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "MISSING_BFT_AUTHORIZATION"

def test_facts_endpoint_invalid_auth():
    headers = {"Authorization": "Bearer invalid_token_here"}
    resp = client.get("/facts?query=all", headers=headers)
    assert resp.status_code == 401
    assert "BFT_SIGNATURE_INVALID" in resp.json()["detail"]

def test_facts_endpoint_valid_auth():
    token = jwt.encode({"user": "borjamoskv"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/facts?query=all", headers=headers)
    assert resp.status_code == 200
    assert "nodes_yield" in resp.json()
    assert resp.json()["authorized_by"] == "borjamoskv"

def test_facts_endpoint_path_traversal_protection():
    token = jwt.encode({"user": "borjamoskv"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/facts?query=../etc/passwd", headers=headers)
    assert resp.status_code == 400
    assert "Query contiene caracteres prohibidos" in resp.json()["detail"]
