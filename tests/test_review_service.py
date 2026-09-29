"""Tests for Review service (Phase 28, Step 2) + AI Writer."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.review import Review
from app.models.tenant import Tenant
from app.models.user import User
from app.services import review_service
from app.services.ai import review_writer


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "rv") -> Tenant:
    t = Tenant(slug=slug, name="Review Biz", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User) -> Booking:
    ci = date.today() - timedelta(days=5)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


def _stub_ai(content: str):
    def _fake(message, *, history=None, provider_name=None):
        return {"content": content, "provider": "stub", "model": "x", "tokens_used": 0}
    return _fake


# ---------- Sentiment ----------


def test_sentiment_positive() -> None:
    out = review_service.compute_sentiment("Amazing stay, clean room, friendly staff", 5)
    assert out["sentiment"] == "positive"
    assert out["score"] > 0.5


def test_sentiment_negative() -> None:
    out = review_service.compute_sentiment("Terrible, dirty and rude staff", 1)
    assert out["sentiment"] == "negative"
    assert out["score"] < -0.5


def test_sentiment_neutral() -> None:
    out = review_service.compute_sentiment("It was fine", 3)
    assert out["sentiment"] == "neutral"


def test_sentiment_rating_prior_dominates() -> None:
    # No lexicon hits: rating drives the score
    out = review_service.compute_sentiment("Standard experience", 5)
    assert out["sentiment"] == "positive"
    out = review_service.compute_sentiment("Standard experience", 1)
    assert out["sentiment"] == "negative"


# ---------- create_review ----------


def test_create_review_minimal(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(
        db, tenant=t, user=u, rating=5, content="Amazing stay, will return!"
    )
    assert r.id
    assert r.sentiment == "positive"
    assert r.status == "published"
    assert r.verified is False


def test_create_review_invalid_rating(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    with pytest.raises(ValueError):
        review_service.create_review(db, tenant=t, user=u, rating=0, content="ok ok ok")
    with pytest.raises(ValueError):
        review_service.create_review(db, tenant=t, user=u, rating=6, content="ok ok ok")


def test_create_review_too_short(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    with pytest.raises(ValueError):
        review_service.create_review(db, tenant=t, user=u, rating=4, content="hi")


def test_create_review_verified_with_booking(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    b = _booking(db, t, u)
    r = review_service.create_review(
        db, tenant=t, user=u, rating=5, content="Great stay, thank you!",
        booking_id=b.id,
    )
    assert r.verified is True


def test_create_review_wrong_booking_rejected(db: Session) -> None:
    t = _tenant(db)
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _booking(db, t, u2)  # belongs to u2
    with pytest.raises(ValueError):
        review_service.create_review(
            db, tenant=t, user=u1, rating=5, content="Nice place ok ok", booking_id=b.id,
        )


# ---------- list / hide / respond ----------


def test_list_reviews_excludes_hidden_by_default(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r1 = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay, loved it")
    r2 = review_service.create_review(db, tenant=t, user=u, rating=4, content="Good experience overall")
    review_service.hide_review(db, t, r2.id)
    rows = review_service.list_reviews(db, t)
    assert len(rows) == 1
    assert rows[0].id == r1.id


def test_list_reviews_include_hidden(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=3, content="Average stay overall")
    review_service.hide_review(db, t, r.id)
    rows = review_service.list_reviews(db, t, include_hidden=True)
    assert len(rows) == 1


def test_set_response_manual(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay, loved it")
    updated = review_service.set_response(db, t, r.id, response_text="Thank you!", provider="manual")
    assert updated.response_text == "Thank you!"
    assert updated.response_provider == "manual"
    assert updated.response_at is not None


def test_set_response_clears_when_empty(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay loved it")
    review_service.set_response(db, t, r.id, response_text="Thank you")
    review_service.set_response(db, t, r.id, response_text="")
    r2 = review_service.get_review(db, t, r.id)
    assert r2.response_text is None
    assert r2.response_at is None


def test_summary(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing, loved it")
    review_service.create_review(db, tenant=t, user=u, rating=5, content="Great stay, very clean")
    review_service.create_review(db, tenant=t, user=u, rating=3, content="It was ok ok ok")
    out = review_service.tenant_review_summary(db, t)
    assert out["total"] == 3
    assert out["avg_rating"] > 4.0
    assert out["by_rating"][5] == 2
    assert out["by_sentiment"].get("positive", 0) >= 2


# ---------- AI polish ----------


def test_polish_review_invalid_language(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        review_writer.polish_review(db, tenant=t, raw_text="some text here", rating=5, language="xx")


def test_polish_review_too_short(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        review_writer.polish_review(db, tenant=t, raw_text="hi", rating=5)


def test_polish_review_ai(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    monkeypatch.setattr(ai_service, "chat", _stub_ai("A lovely room with a wonderful view."))
    t = _tenant(db)
    out = review_writer.polish_review(db, tenant=t, raw_text="room nice view good", rating=5)
    assert out["provider"] == "ai"
    assert "lovely room" in out["content"]


def test_polish_review_fallback(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    out = review_writer.polish_review(db, tenant=t, raw_text="nice room and friendly staff", rating=5)
    assert out["provider"] == "fallback"
    assert "nice room" in out["content"]


# ---------- AI respond ----------


def test_respond_invalid_tone(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay loved it")
    with pytest.raises(ValueError):
        review_writer.respond_to_review(db, tenant=t, review=r, tone="sarcastic")


def test_respond_ai(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    monkeypatch.setattr(ai_service, "chat", _stub_ai("Thank you so much for your kind words!"))
    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay loved it")
    out = review_writer.respond_to_review(db, tenant=t, review=r)
    assert out["provider"] == "ai"
    assert "Thank you" in out["response"]


def test_respond_fallback_negative(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t)
    r = review_service.create_review(db, tenant=t, user=u, rating=1, content="Terrible, dirty and rude")
    out = review_writer.respond_to_review(db, tenant=t, review=r)
    assert out["provider"] == "fallback"
    assert "sorry" in out["response"].lower() or "sorry" in out["response"].lower()
