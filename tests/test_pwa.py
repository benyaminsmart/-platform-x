"""Tests for PWA setup (Phase 30, Step 8)."""
from pathlib import Path
from fastapi.testclient import TestClient


def test_manifest_served(client: TestClient) -> None:
    r = client.get("/static/manifest.webmanifest")
    assert r.status_code == 200
    assert "Platform-X" in r.text
    assert "standalone" in r.text
    assert "theme_color" in r.text


def test_service_worker_served(client: TestClient) -> None:
    r = client.get("/static/sw.js")
    assert r.status_code == 200
    assert "CACHE" in r.text
    assert "install" in r.text


def test_icon_served(client: TestClient) -> None:
    r = client.get("/static/icons/icon.svg")
    assert r.status_code == 200
    assert "svg" in r.text.lower()


def test_base_layout_has_manifest(client: TestClient) -> None:
    r = client.get("/")
    html = r.text
    assert 'rel="manifest"' in html
    assert 'theme-color' in html
    assert 'serviceWorker' in html


def test_manifest_file_valid() -> None:
    import json
    data = json.loads(Path("app/static/manifest.webmanifest").read_text(encoding="utf-8"))
    assert data["name"].startswith("Platform-X")
    assert data["display"] == "standalone"
    assert len(data["icons"]) >= 1
    assert data["icons"][0]["type"] == "image/svg+xml"
