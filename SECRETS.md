# Platform-X — Secrets Management

> How to handle sensitive configuration values safely.

## Rules

1. **Never commit secrets to Git.**
   - `.env` is in `.gitignore`
   - Only `.env.example` (with placeholder values) is committed

2. **Different secrets per environment.**
   - Development: throwaway values
   - Staging: separate secrets
   - Production: strong, unique

3. **SECRET_KEY must be:**
   - At least 32 characters
   - Random (not guessable)
   - Different for each environment
   - Rotated if compromised

4. **In production:**
   - Use environment variables (not `.env` file)
   - Or use a secrets manager (Doppler, AWS Secrets Manager, Vault)
   - Rotate on a schedule

## Production checklist

- [ ] SECRET_KEY set to random 64-char value
- [ ] DATABASE_URL points to PostgreSQL with strong password
- [ ] APP_DEBUG=false
- [ ] APP_ENV=production
- [ ] ENABLE_MOCK_PAYMENTS=false
- [ ] CORS_ORIGINS = real domain(s)
- [ ] Telr (payment) API keys set (when integrated)
- [ ] Email provider keys set
- [ ] SMS provider keys set
- [ ] No .env file on server (use env vars)
- [ ] .env excluded from all backup scripts

## Generating a strong SECRET_KEY

python -c "import secrets; print(secrets.token_urlsafe(64))"

## Rotating SECRET_KEY

1. Generate a new value
2. Update environment variable
3. Restart the server
4. Note: All existing JWT tokens become invalid (users must re-login)
5. Announce if needed

## What NEVER goes in Git

- .env files (any environment)
- Database files (*.db)
- Private keys (*.pem, *.key)
- Payment provider credentials
- Email/SMS API keys
- Backup archives
- Logs
