"""Seed a demo business owner user for a tenant.

Run: python -m app.scripts.seed_business_user
Creates owner@trianon-hotel.local as business owner of trianon-hotel.
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User


DEMO = [
    {
        "tenant_slug": "trianon-hotel",
        "email": "owner@trianon-hotel.com",
        "password": "OwnerPass123",
        "first_name": "Trianon",
        "last_name": "Owner",
        "business_role": "owner",
    },
    {
        "tenant_slug": "saffron-restaurant",
        "email": "owner@saffron-restaurant.com",
        "password": "OwnerPass123",
        "first_name": "Saffron",
        "last_name": "Owner",
        "business_role": "owner",
    },
]


def seed():
    created = 0
    with SessionLocal() as db:
        for data in DEMO:
            tenant = db.execute(
                select(Tenant).where(Tenant.slug == data["tenant_slug"])
            ).scalar_one_or_none()
            if not tenant:
                print(f"! tenant {data['tenant_slug']} not found")
                continue
            existing = db.execute(
                select(User).where(
                    User.tenant_id == tenant.id,
                    User.email == data["email"],
                )
            ).scalar_one_or_none()
            if existing:
                # Update business_role if needed
                if not existing.business_role:
                    existing.business_role = data["business_role"]
                    db.commit()
                print(f"  updated {data['email']}")
                continue
            import secrets
            user = User(
                tenant_id=tenant.id,
                email=data["email"],
                password_hash=hash_password(data["password"]),
                first_name=data["first_name"],
                last_name=data["last_name"],
                business_role=data["business_role"],
                referral_code=secrets.token_urlsafe(8).replace("-","").replace("_","")[:10].upper(),
            )
            db.add(user)
            db.commit()
            created += 1
            print(f"  created {data['email']}")
    print(f"Done. Created {created}.")


if __name__ == "__main__":
    seed()
