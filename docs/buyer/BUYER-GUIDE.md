# Platform-X — Buyer Guide (First 30 Minutes)

## Minute 0-5 — read
- README, docs/00-NEW-CHAT-QUICKSTART.md, HANDOFF.md
- docs/buyer/TECH-OVERVIEW.md

## Minute 5-15 — install
1. SSH to your VPS
2. sudo bash scripts/deploy/install.sh <domain> <repo_url>
3. Save the DB password printed by the script

## Minute 15-25 — configure
1. sudo -u platformx nano /opt/platform-x/.env
   - SECRET_KEY (generate new)
   - CORS_ORIGINS=["https://<domain>"]
   - AI_API_KEY (if using real provider)
   - ENABLE_MOCK_PAYMENTS=false
2. cd /opt/platform-x
   sudo -u platformx ./venv/bin/alembic upgrade head
   sudo -u platformx ./venv/bin/python -m app.scripts.seed_all

## Minute 25-30 — start + verify
1. sudo systemctl start platform-x
2. sudo certbot --nginx -d <domain> -d www.<domain>
3. bash scripts/smoke_test.sh https://<domain>

## You are live
- Guest: https://<domain>/
- Admin: https://<domain>/platform/login
- API docs: https://<domain>/docs/api
- Wallet: https://<domain>/account/wallet

## Next 7 days
- Add your first business (platform admin -> approve tenant)
- Test one real payment end-to-end
- Configure AI provider
- Set up nightly backups (see OPERATIONS.md)

## Ongoing
- Weekly: check logs + backups
- Monthly: review reward economics
- Quarterly: update dependencies

## Support
- Docs: docs/buyer/
- Community: none yet
- Paid: activation + training (see HANDOVER-CHECKLIST.md)
