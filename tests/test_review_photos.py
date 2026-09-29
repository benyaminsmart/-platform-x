"""Tests for review photos (Phase 39, Step 1)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.tenant import Tenant
from app.models.user import User
from app.services import review_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def _make_review(db, t, u):
    return review_service.create_review(
        db, tenant=t, user=u, rating=5, content="Amazing stay, loved it"
    )


def _upload(client, h, rid, *, name="x.jpg", ctype="image/jpeg", data=b"fake-image-bytes"):
    return client.post(
        f"/reviews/{rid}/photos",
        files={"file": (name, data, ctype)},
        headers=h,
    )


def test_upload_ok(client, db):
    t = _tenant(db, "rp-ok")
    u = _user(db, t)
    r = _make_review(db, t, u)
    resp = _upload(client, _h(u, t), r.id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["url"].startswith("/static/uploads/reviews/")
    assert body["position"] == 0


def test_upload_rejects_wrong_type(client, db):
    t = _tenant(db, "rp-badtype")
    u = _user(db, t)
    r = _make_review(db, t, u)
    resp = _upload(client, _h(u, t), r.id, ctype="application/pdf")
    assert resp.status_code == 400


def test_upload_max_3(client, db):
    t = _tenant(db, "rp-max")
    u = _user(db, t)
    r = _make_review(db, t, u)
    h = _h(u, t)
    for i in range(3):
        resp = _upload(client, h, r.id, name=f"{i}.jpg")
        assert resp.status_code == 201
    resp = _upload(client, h, r.id, name="4.jpg")
    assert resp.status_code == 400


def test_upload_other_user_403(client, db):
    t = _tenant(db, "rp-other")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    r = _make_review(db, t, u2)
    resp = _upload(client, _h(u1, t), r.id)
    assert resp.status_code == 403


def test_list_photos_public(client, db):
    t = _tenant(db, "rp-list")
    u = _user(db, t)
    r = _make_review(db, t, u)
    _upload(client, _h(u, t), r.id)
    resp = client.get(f"/reviews/{r.id}/photos")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_delete_photo(client, db):
    t = _tenant(db, "rp-del")
    u = _user(db, t)
    r = _make_review(db, t, u)
    h = _h(u, t)
    up = _upload(client, h, r.id).json()
    resp = client.delete(f"/reviews/{r.id}/photos/{up['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert client.get(f"/reviews/{r.id}/photos").json() == []
