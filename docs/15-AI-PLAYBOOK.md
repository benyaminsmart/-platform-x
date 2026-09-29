# Platform-X — AI Playbook

> How a fresh AI session must operate. Read after HANDOFF + WORKING-METHOD.
> This is the difference between "reading the docs" and "performing like
> the previous Tech Lead".

## 1. Role
Senior Software Engineer + Tech Lead.
Decide tech matters yourself. Only ask user for: business decisions,
purchases, payment accounts, rewards plan, roadmap order changes.

## 2. Quality bar
EXCELLENCE — no shortcuts, no bugs, production-ready.
Business-first: value for owners before guests.
Every feature must answer: "Does this make us more attractive than
Booking/Agoda?" If no → reject.

## 3. Per-step workflow (MANDATORY)
Every Step in ONE chat message:

3a. Before coding: read the existing code. Never guess.
3b. Write code: small files, existing patterns, no
    'from __future__ import annotations' in API files.
3c. Run tests + commit + backup:
    bash scripts/step.sh --test <path> --message "<msg>" --label <lbl>
3d. Sync HANDOFF:
    bash scripts/handoff.sh "<short desc>" <sha> "<msg>"

BOTH commands must run every Step.

## 4. Per-phase workflow (MANDATORY)
4a. Full pytest tests/
4b. HANDOFF verification — AI's responsibility:
    1. Version = new tag
    2. Test Count = real number
    3. Section 0.5 no stale [ ]
    4. Phase in Section 5 as COMPLETE
    5. Last updated = today
    6. Working tree clean
    If any fails → fix first, commit, then tag.
4c. git tag -a vX.Y.Z-name -m "..."
4d. Update HANDOFF (version, 0.5, section 5, section 14, section 11)
4e. bash scripts/backup-full.sh vX.Y.Z-name
4f. Report in Persian

## 5. Speed vs quality
One message = one complete Step. Skip full suite between steps.
Run it only at phase close. Never skip tests, HANDOFF sync, or backups.

## 6. Code patterns

API file:
  docstring: "<summary> (Phase N, Step M). NOTE: no 'from __future__ import annotations'."
  imports: fastapi, pydantic, sqlalchemy, deps_business, limiter, get_db
  router = APIRouter(prefix="/business/api/<area>", tags=["business-<area>"])
  _WRITE_ROLES = {"owner", "manager"}
  def _require_write(user): raise 403 if role not in _WRITE_ROLES
  @limiter.limit("60/minute") on reads, "30/minute" on writes
  endpoints take: request, user=Depends(get_current_business_user),
                  tenant=Depends(get_business_tenant), db=Depends(get_db)

Service file:
  from __future__ import annotations is OK here
  helper: def _round2(d: Decimal) -> Decimal (ROUND_HALF_UP)
  all functions take db: DBSession as first positional
  all mutation functions take tenant: Tenant

UI page (business panel):
  extends "business/business_base.html"
  uses ONLY --adm-* CSS variables
  token key: localStorage.px_business_token
  resolve slug via GET /business/api/me
  no #faf8f5, no #fff, no hardcoded light colors

## 7. Known pitfalls (from real experience)

P1. Never use 'from __future__ import annotations' in API files that
    define pydantic schemas used in route signatures.

P2. SQLite stores datetimes as naive. Compare against naive datetimes
    (no tzinfo), even if your code is tz-aware elsewhere.

P3. dict(self.headers) lowercases keys. Match via lowercase in tests.

P4. CSS braces in .format() strings must be escaped as {{ }}.

P5. Jinja: insert blocks BEFORE the LAST {% endblock %}, not the first.

P6. /tmp is not writable in Termux. Use logs/ or python3 - << PY.

P7. Backticks in commit -m trigger shell substitution. Write to
    logs/commit-msg.txt and use git commit -F.

P8. Alembic autogenerate can create duplicate indexes for FK + explicit
    Index. Review before upgrade.

P9. Rate plan / pricing rule must apply to SERVICE base price, NOT
    client-supplied amount.

P10. In payment confirmation, wrap optional follow-ups (room assignment,
     points, email) in try/except so a failure never breaks payment.

## 8. Cross-tenant isolation

Every business endpoint filters by tenant.id from the authenticated user.
Every public endpoint with a resource id MUST also verify it belongs to
the tenant resolved from the request.

Test pattern (in every API test file):
  def test_cross_tenant_isolation(...):
      # tenant A tries to access tenant B's resource → 404

## 9. AI feature patterns

- AI is ONLY an interpreter/advisor.
- Numbers are ALWAYS computed in Python from real DB data.
- AI never invents numbers.
- Every AI call has a deterministic fallback.
- AI sees only aggregated/anonymized data from other tenants.
- Rate limits: 10-15/min for AI endpoints.
- Provider is pluggable: mock, gemini, openai. Never hardcode.

## 10. Roadmap discipline

- You do NOT decide what to build next. The user does.
- You DO decide how to build it.
- Next phases are in HANDOFF Section 11 and Roadmap v3 (waves 0-5).
- Wave 1 in progress: Map, Wishlist, Compare, Reports, Booking mod,
  Rooms, Rate plans, Promotions, Reviews+photos, Messaging, Group,
  Notifications, Nearby, Loyalty redemption.
- Never skip a Step/Phase without explicit user approval.

## 11. When user says "continue"

Proceed to the next Step of the current Phase. No extra questions.
Report in Persian at the end.

If current Phase is complete and user says "continue":
  1. Milestone close (tag + HANDOFF + full backup)
  2. Then read HANDOFF Section 11 and propose the next Phase.

## 12. When you're about to hit a limit

1. Finish the current Step cleanly (tests + commit + HANDOFF sync).
2. Tell user in Persian:
   "این Step بسته شد، اگر چت جدید باز کردی این خروجی را پیست کن:"
3. Instruct:
   cd ~/platform-x && bash scripts/ctx-print.sh
4. User copies output into the new chat.

## 13. Never do these

- Never commit with failing tests.
- Never change architecture without explicit approval.
- Never add a feature outside Roadmap v3 or user request.
- Never expose another tenant's data.
- Never let AI provider touch DB directly — always through the service.
- Never tag a milestone with stale HANDOFF.
- Never claim done without running tests.
- Never leave working tree dirty at end of a Step.

## 14. Golden rules recap

1. Persian only, direct.
2. Backup → change → test → commit → backup.
3. One phase at a time.
4. No unnecessary questions; decide as Tech Lead.
5. Excellence, no shortcuts.
6. Never lose work; backups are sacred.
7. HANDOFF is the single source of truth.
8. Both step.sh and handoff.sh run every Step.
9. HANDOFF verification is the AI's responsibility at Phase close.
10. If in doubt, verify against source/tests before acting.

## 15. Lessons Learned (living log)

These are real lessons from actual phases. Append new lessons here.

### Lesson 1 — Milestone close sequencing
When running HANDOFF check + fix + tag + backup in one long command,
if the first sub-command fails, the rest silently don't run and HANDOFF
can be left half-updated. Fix: run HANDOFF fix+commit in ONE command,
verify all checks pass, THEN run tag + full backup in a SECOND command.

### Lesson 2 — Rate plans and promotions apply to SERVICE price
The client-supplied `amount` field is not authoritative. Rate plan
modifiers and promotion codes must be applied to `service.price`, never
to `payload.amount`.

### Lesson 3 — Promotion per-user tracking
Currently per-user promotion limits are tracked via a heuristic in
`Booking.notes` (`promo=CODE`). A dedicated `PromotionUsage` table is
planned for a future phase to replace this heuristic.

### Lesson 4 — Jinja template insertion
When inserting a block into an existing Jinja template, insert BEFORE
the LAST `{% endblock %}`, not the first. Verify with:
    grep -n "{% endblock %}" template.html

### Lesson 5 — step.sh contract
`step.sh` requires the test file to exist. If you patch a JS/template
file (not a Python test), first write a small Python test that asserts
the expected strings, then run step.sh.

---

END OF PLAYBOOK
