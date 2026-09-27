"""Partner application service."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.partner_application import PartnerApplication
from app.schemas.partner import PartnerApplicationCreate


def create_application(
    db: DBSession, payload: PartnerApplicationCreate
) -> PartnerApplication:
    """Save a new partner application."""
    app = PartnerApplication(
        tenant_type=payload.tenant_type,
        contact_name=payload.contact_name.strip(),
        contact_role=payload.contact_role.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip(),
        whatsapp=(payload.whatsapp or "").strip() or None,
        business_name=payload.business_name.strip(),
        brand_name=(payload.brand_name or "").strip() or None,
        city=payload.city.strip(),
        address=payload.address.strip(),
        website=(payload.website or "").strip() or None,
        instagram=(payload.instagram or "").strip() or None,
        founded_year=payload.founded_year,
        staff_count=payload.staff_count,
        tier_interest=payload.tier_interest,
        languages=payload.languages,
        about=payload.about,
        motivation=payload.motivation,
        details=payload.details or {},
        status="new",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def list_applications(
    db: DBSession,
    *,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[PartnerApplication], int]:
    """Return (applications, total)."""
    filters = []
    if status:
        filters.append(PartnerApplication.status == status)

    total = db.execute(
        select(func.count()).select_from(PartnerApplication).where(*filters)
    ).scalar_one()

    stmt = (
        select(PartnerApplication)
        .where(*filters)
        .order_by(PartnerApplication.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total
