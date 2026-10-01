"""Tests for Business Peer Benchmark page (Phase 52, Step 3).

When the visitor is not authenticated, business_base.html omits the
content block entirely (client-side auth guard). Only the <title>,
shared scripts, and the block-scripts JS render. Tests therefore
assert on those, plus we verify the route + sidebar link.
"""
from fastapi.testclient import TestClient


def test_page_renders_title(client: TestClient) -> None:
    r = client.get("/business/peer-benchmark")
    assert r.status_code == 200
    body = r.text
    assert "Peer Benchmark" in body  # <title> is always present


def test_page_script_calls_api(client: TestClient) -> None:
    r = client.get("/business/peer-benchmark")
    body = r.text
    assert "/business/api/peer-benchmark" in body
    assert "pb-metrics" in body
    assert "pb-summary" in body
    assert "pb-refresh" in body
    assert "pb-lang" in body


def test_sidebar_link_present(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    body = r.text
    assert "/business/peer-benchmark" in body
