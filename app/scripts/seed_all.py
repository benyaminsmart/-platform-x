"""Run all seed scripts in order.

Run: python -m app.scripts.seed_all
"""

from app.scripts import seed_admin, seed_services, seed_tenants
from app.db.session import SessionLocal


def main() -> None:
    print("=== Seeding tenants ===")
    with SessionLocal() as db:
        created, skipped = seed_tenants.seed(db)
        print(f"tenants: created={created}, skipped={skipped}")

    print("=== Seeding services ===")
    with SessionLocal() as db:
        created, skipped = seed_services.seed(db)
        print(f"services: created={created}, skipped={skipped}")

    print("=== Seeding platform admin ===")
    seed_admin.main()

    print("=== Done ===")


if __name__ == "__main__":
    main()
