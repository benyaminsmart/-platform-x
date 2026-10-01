"""Tests for Business Peer Benchmark page (Phase 52, Step 3)."""
from fastapi.testclient import TestClient


def test_page_renders(client: TestClient) -> None:
    r = client.get("/business/peer-benchmark")
    assert r.status_code == 200
    body = r.text
    assert "Deep Peer Benchmark" in body
    assert 'id="pb-metrics"' in body
    assert 'id="pb-summary"' in body
    assert 'id="pb-refresh"' in body
    assert 'id="pb-lang"' in body


def test_page_calls_api(client: TestClient) -> None:
    r = client.get("/business/peer-benchmark")
    body = r.text
    assert "/business/api/peer-benchmark" in body


def test_sidebar_link_present(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    body = r.text
    assert "/business/peer-benchmark" in body
