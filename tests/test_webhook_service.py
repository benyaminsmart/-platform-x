"""Tests for Webhook service (Phase 14, Step 4)."""

import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery
from app.services import webhook_service


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "wh") -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


class _Receiver(BaseHTTPRequestHandler):
    received: list[dict] = []
    respond_with: int = 200

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        # Store headers with lowercase keys for case-insensitive lookup
        _Receiver.received.append({
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        })
        self.send_response(_Receiver.respond_with)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args, **kwargs):
        pass  # silence


def _start_receiver(respond_with: int = 200) -> tuple[HTTPServer, int]:
    _Receiver.received = []
    _Receiver.respond_with = respond_with
    server = HTTPServer(("127.0.0.1", 0), _Receiver)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


# ---------- URL validation ----------


def test_validate_url_https_ok() -> None:
    assert webhook_service.validate_url("https://example.com/hook")


def test_validate_url_http_localhost_ok() -> None:
    assert webhook_service.validate_url("http://127.0.0.1:9000/hook")
    assert webhook_service.validate_url("http://localhost:9000/hook")


def test_validate_url_http_public_raises() -> None:
    with pytest.raises(ValueError):
        webhook_service.validate_url("http://example.com/hook")


def test_validate_url_bad_scheme_raises() -> None:
    with pytest.raises(ValueError):
        webhook_service.validate_url("ftp://example.com")


# ---------- Events validation ----------


def test_validate_events_ok() -> None:
    assert webhook_service.validate_events(["booking.created"])


def test_validate_events_empty_raises() -> None:
    with pytest.raises(ValueError):
        webhook_service.validate_events([])


def test_validate_events_unknown_raises() -> None:
    with pytest.raises(ValueError):
        webhook_service.validate_events(["bogus.event"])


# ---------- CRUD ----------


def test_register_returns_plaintext_once(db: Session) -> None:
    t = _tenant(db)
    row, secret = webhook_service.register_webhook(
        db, tenant=t, name="Test", url="https://example.com/h", events=["booking.created"],
    )
    assert secret.startswith("whsec_")
    assert row.secret_hashed != secret
    s = webhook_service.serialize_webhook(row)
    assert "secret_hashed" not in s


def test_register_empty_name_raises(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        webhook_service.register_webhook(
            db, tenant=t, name="", url="https://example.com/h", events=["booking.created"],
        )


def test_list_webhooks_only_own(db: Session) -> None:
    t1 = _tenant(db, "w1")
    t2 = _tenant(db, "w2")
    webhook_service.register_webhook(db, tenant=t1, name="A", url="https://example.com/a", events=["booking.created"])
    webhook_service.register_webhook(db, tenant=t2, name="B", url="https://example.com/b", events=["booking.created"])
    rows = webhook_service.list_webhooks(db, t1)
    assert len(rows) == 1
    assert rows[0].name == "A"


def test_delete_webhook(db: Session) -> None:
    t = _tenant(db)
    row, _ = webhook_service.register_webhook(
        db, tenant=t, name="X", url="https://example.com/h", events=["booking.created"],
    )
    updated = webhook_service.delete_webhook(db, t, row.id)
    assert updated is not None
    assert updated.active is False


def test_delete_wrong_tenant(db: Session) -> None:
    t1 = _tenant(db, "d1")
    t2 = _tenant(db, "d2")
    row, _ = webhook_service.register_webhook(
        db, tenant=t1, name="X", url="https://example.com/h", events=["booking.created"],
    )
    assert webhook_service.delete_webhook(db, t2, row.id) is None


# ---------- Delivery ----------


def test_deliver_success(db: Session) -> None:
    server, port = _start_receiver(respond_with=200)
    try:
        t = _tenant(db, "deliver")
        row, secret = webhook_service.register_webhook(
            db, tenant=t, name="Local",
            url=f"http://127.0.0.1:{port}/hook",
            events=["booking.created"],
        )
        delivery = webhook_service.deliver(
            db, webhook=row, plaintext_secret=secret,
            event_type="booking.created",
            payload={"id": "b-1", "amount": 500},
        )
        assert delivery.success is True
        assert delivery.status_code == 200

        # Verify signature
        assert len(_Receiver.received) == 1
        rec = _Receiver.received[0]
        body = rec["body"]
        sig_header = rec["headers"]["x-platformx-signature"]
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        assert sig_header == expected
        assert rec["headers"]["x-platformx-event"] == "booking.created"

        # Webhook row updated
        db.refresh(row)
        assert row.last_status_code == 200
        assert row.last_success_at is not None
    finally:
        server.shutdown()


def test_deliver_failure_5xx(db: Session) -> None:
    server, port = _start_receiver(respond_with=500)
    try:
        t = _tenant(db, "deliver-fail")
        row, secret = webhook_service.register_webhook(
            db, tenant=t, name="Local",
            url=f"http://127.0.0.1:{port}/hook",
            events=["booking.created"],
        )
        delivery = webhook_service.deliver(
            db, webhook=row, plaintext_secret=secret,
            event_type="booking.created",
            payload={"x": 1},
        )
        assert delivery.success is False
        assert delivery.status_code == 500
        db.refresh(row)
        assert row.failure_count == 1
        assert row.last_failure_at is not None
    finally:
        server.shutdown()


def test_deliver_unreachable(db: Session) -> None:
    t = _tenant(db, "deliver-dead")
    row, secret = webhook_service.register_webhook(
        db, tenant=t, name="Dead",
        url="http://127.0.0.1:1/hook",  # nothing listening
        events=["booking.created"],
    )
    delivery = webhook_service.deliver(
        db, webhook=row, plaintext_secret=secret,
        event_type="booking.created",
        payload={"x": 1},
    )
    assert delivery.success is False
    assert delivery.error is not None
    assert db.query(WebhookDelivery).count() == 1
