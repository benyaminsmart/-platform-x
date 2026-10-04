# Platform-X — Transfer Guide

## 1. Repository
- Transfer ownership of the git repo to the buyer's GitHub/GitLab account.
- Alternative: buyer creates an empty repo, seller pushes all branches+tags:
    git push --mirror <new-repo-url>
- Confirm the buyer sees all tags: git tag --sort=-creatordate

## 2. Secrets
The seller must NEVER ship real secrets. The buyer generates their own.
- SECRET_KEY      -> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
- DATABASE_URL    -> buyer's own PostgreSQL
- AI_API_KEY      -> buyer's own provider key
- PAYMENT_*       -> buyer's own Telr/Stripe account
- EMAIL_*         -> buyer's own Resend account
Verify with: grep -rE "SECRET|KEY|TOKEN" .env (should be placeholders)

## 3. Database
Recommended: buyer starts with an empty DB.
- alembic upgrade head
- python -m app.scripts.seed_all
If seller transfers data:
- pg_dump from seller -> pg_restore to buyer
- Remove demo users before handover

## 4. Domain
- Buyer registers/points their domain to their VPS
- Run: sudo certbot --nginx -d <domain> -d www.<domain>

## 5. Payment provider
- Buyer opens a Telr or Stripe merchant account (own KYC)
- Add keys to .env
- Set ENABLE_MOCK_PAYMENTS=false
- Test a real transaction end-to-end

## 6. AI provider
- Buyer creates a Gemini/OpenAI/Anthropic API key
- Add to .env
- Test one AI feature end-to-end

## 7. First smoke test
bash scripts/smoke_test.sh https://<domain>

## 8. Communication
- 30-day handover window
- Paid support available (see HANDOVER-CHECKLIST.md)

## 9. What NOT to do
- Do not commit .env
- Do not reuse seller's secrets
- Do not run production with APP_DEBUG=true
- Do not skip migrations
