# Platform-X — Operations Guide

## 1. Daily checks
- Service: systemctl status platform-x
- Logs:    journalctl -u platform-x -n 50
- Disk:    df -h
- DB:      psql "$DATABASE_URL" -c "SELECT 1"

## 2. Logs
- App:   journalctl -u platform-x -f
- Nginx: tail -f /var/log/nginx/access.log /var/log/nginx/error.log
- Backup: /var/log/platform-x/backup.log

## 3. Backups
Nightly (crontab):
  0 3 * * * /opt/platform-x/scripts/deploy/backup.sh >> /var/log/platform-x/backup.log 2>&1

Backups live in /var/backups/platform-x/ (last 14 kept).

Manual backup:
  bash scripts/deploy/backup.sh manual

Restore:
  sudo bash scripts/deploy/restore.sh <archive.tar.gz>

Offsite: rsync to a second VPS or push to S3.

## 4. Updates
  sudo bash scripts/deploy/update.sh main
Rollback:
  cd /opt/platform-x && sudo -u platformx git checkout <tag>
  sudo -u platformx ./venv/bin/alembic downgrade -1
  sudo systemctl restart platform-x

## 5. Migrations
Apply:  sudo -u platformx ./venv/bin/alembic upgrade head
Current: sudo -u platformx ./venv/bin/alembic current
History: sudo -u platformx ./venv/bin/alembic history

## 6. Common issues
| Symptom | Fix |
|---------|-----|
| 502 Bad Gateway | systemctl restart platform-x |
| DB connection refused | check DATABASE_URL + postgresql service |
| Slow responses | check N+1 in logs; scale workers |
| Disk full | prune backups; rotate logs |
| Auth 401 in browser | check CORS_ORIGINS |

## 7. Scaling
- Vertical: bump VPS to 4 vCPU / 8 GB RAM; uvicorn --workers 4
- Horizontal: multiple app servers behind nginx upstream + shared Postgres
- Caching: add Redis (optional; not required today)

## 8. Monitoring (recommended)
- Uptime: UptimeRobot / BetterStack
- Logs: Loki / Datadog
- Metrics: /metrics (Prometheus) if enabled
- Alerts: email on 5xx rate + service down

## 9. Support
See `HANDOVER-CHECKLIST.md` for what is included vs paid support.
