# Platform-X — Project Rules

> **Quality Level: EXCELLENCE**
> Every line of code must be clean, tested, documented, and production-ready.

---

## 1. Code Quality Standards

### General
- No bugs tolerated. Every feature must be tested before commit.
- No dead code. Remove anything unused immediately.
- No commented-out code. Git history preserves old versions.
- No TODO comments. If it needs to be done, do it now or create an issue.

### Naming
- Python: snake_case for variables/functions, PascalCase for classes.
- Files: snake_case.py for Python, kebab-case or snake_case for docs.
- Constants: UPPER_SNAKE_CASE.
- Be descriptive. get_user_by_email not getUser.

### Structure
- One responsibility per file.
- One responsibility per function.
- Maximum function length: ~50 lines (split if longer).
- Maximum file length: ~500 lines (split if longer).

### Security (Non-negotiable)
- Never hard-code secrets (use .env).
- Never trust user input (validate everything).
- Never store passwords in plaintext (hash with salt).
- Never log sensitive data.
- Always use HTTPS in production.
- Always validate session tokens on every request.

---

## 2. Working Rules

### Rule 1 — Backup Before Every Change
Before modifying any file:
cp path/file.ext "backups/file-before-CHANGE-$(date +%Y%m%d-%H%M%S)"

### Rule 2 — One Step at a Time
- One change, test, confirm, next change.
- No batch changes.
- If 2 attempts fail, try a completely different approach.
- Never make the same mistake 3 times.

### Rule 3 — Commit After Each Success
- Descriptive commit messages (what + why).
- Format: type: short description (feat, fix, docs, refactor, test)
- Example: feat: add user registration endpoint

### Rule 4 — Test Before Claiming Done
- Every feature tested end-to-end.
- Backend: curl or test script.
- Frontend: manual test in browser.
- No "it should work" — verify it works.

### Rule 5 — Documentation
- Every module has a docstring.
- Every API endpoint documented.
- Every architectural decision recorded in PROJECT-NOTES.md.
- Every phase documented in HANDOFF.md.

### Rule 6 — No Silent Failures
- All errors logged.
- All exceptions handled.
- All edge cases covered.

---

## 3. Testing Requirements

### Phase 1 (MVP)
- Manual testing by developer.
- Smoke tests (does it work at all?).

### Phase 2+
- Unit tests for all business logic (pytest).
- Integration tests for all API endpoints.
- End-to-end tests for critical flows (booking, payment).
- Coverage target: 80%+

### Continuous
- Every commit should pass all tests.
- No merge without passing tests.

---

## 4. Git Workflow

- Single branch: main
- Small, frequent commits
- Descriptive messages
- No WIP commits in main
- Tags for releases: v0.1.0, v0.2.0, etc.

### Commit Message Format
type: short description (max 72 chars)

Optional longer description explaining why.

Types: feat, fix, docs, style, refactor, test, chore

---

## 5. Backup Strategy

### Per Change
- Before modifying any file → file backup.

### Per Session
- At end of work session → full project backup to backups/checkpoint-YYYYMMDD-HHMMSS/

### Per Phase
- After completing a phase → tagged release in git + full backup.

---

## 6. Forbidden Practices

- Hard-coded URLs, secrets, or configuration
- alert() for debugging (use proper logging)
- console.log() left in production code
- Abandoned test files
- Empty commits or vague messages
- "I'll fix it later"
- Copy-paste without understanding
- Silent error handling
- Trusting client input
- Mixing business logic with presentation

---

## 7. Platforms & Surfaces

Platform-X will serve users across multiple surfaces:

1. Web Platform (primary)
2. REST API (for integrations)
3. Mobile Application (iOS + Android)
4. Telegram Bot (guest services, notifications)

All surfaces must be:
- Consistent in behavior
- Secured with same auth rules
- Documented
- Tested

---

## 8. Documentation Standards

Every folder contains a README.md explaining its contents.
Every complex function has a docstring.
Every API endpoint has:
- Purpose
- Request format
- Response format
- Error cases

---

## 9. Performance Standards

- API response time: < 200ms (normal), < 500ms (complex)
- Page load: < 2s on mobile 3G
- Database queries: optimized, indexed
- No N+1 queries
- Caching where appropriate

---

## 10. Accessibility

- WCAG 2.1 AA compliance for all user-facing pages
- Keyboard navigation
- Screen reader compatible
- High contrast mode friendly

---

Last updated: September 2026
Status: Active and enforced from day one.
