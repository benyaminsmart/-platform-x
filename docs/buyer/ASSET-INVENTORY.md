# Platform-X — Asset Inventory

## Code
- Python files: 240+ | Lines: 32,000+
- Services: 60+ | Models: 46+ | Endpoints: 220+
- Templates: 81 | Migrations: 15+

## Tests
- 1502 automated tests
- ~60 seconds parallel execution
- Files: 200+ test modules

## Tags (shipping milestones)
See: git tag --sort=-creatordate
Recent: v0.60.3-smoke-and-docs, v0.60.2-deploy-scripts,
v0.60.1-env-config, v0.60.0-rewards-complete

## Documentation
- docs/00-NEW-CHAT-QUICKSTART.md
- docs/01..16 (architecture, roadmap, data model, API, security, etc.)
- docs/14-ROADMAP-V3-COMPETITIVE.md
- docs/15-AI-PLAYBOOK.md
- docs/16-MASTER-ROADMAP.md
- docs/DEPLOY-CHECKLIST.md
- docs/buyer/ (this folder: 8 files)

## Deployment assets
- scripts/deploy/install.sh
- scripts/deploy/update.sh
- scripts/deploy/backup.sh
- scripts/deploy/restore.sh
- scripts/smoke_test.sh
- deploy/platform-x.service (systemd)
- deploy/nginx.conf (reverse proxy)
- .env.example (120 lines, commented)

## Commercial assets
- SELLING-PITCH (buyer-facing)
- PDF-ready version
- docs/buyer/ (this folder)

## What is NOT in the package
- Seller's production DB
- Seller's secrets / .env
- Seller's third-party accounts
- Seller's demo data (removed in Phase 88)
