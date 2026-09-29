"""Tests for Message model (Phase 39, Step 4)."""
from sqlalchemy.orm import Session
from app.models.message import Message
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_create_message(db):
    t = _tenant(db, "msg-create")
    m = Message(
        tenant_id=t.id, thread_id="thread-1", booking_id=None,
        sender_user_id="user-1", sender_role="user", body="Hello",
    )
    db.add(m); db.commit(); db.refresh(m)
    assert m.id
    assert m.sender_role == "user"
    assert m.read_at_user is None


def test_messages_same_thread(db):
    t = _tenant(db, "msg-thread")
    db.add(Message(tenant_id=t.id, thread_id="t1", sender_role="user", body="a"))
    db.add(Message(tenant_id=t.id, thread_id="t1", sender_role="business", body="b"))
    db.add(Message(tenant_id=t.id, thread_id="t2", sender_role="user", body="c"))
    db.commit()
    t1_rows = db.query(Message).filter(Message.thread_id == "t1").all()
    assert len(t1_rows) == 2
    t2_rows = db.query(Message).filter(Message.thread_id == "t2").all()
    assert len(t2_rows) == 1


def test_message_defaults(db):
    t = _tenant(db, "msg-def")
    m = Message(tenant_id=t.id, thread_id="x", sender_role="user", body="hi")
    db.add(m); db.commit(); db.refresh(m)
    assert m.booking_id is None
    assert m.sender_user_id is None
    assert m.read_at_business is None
