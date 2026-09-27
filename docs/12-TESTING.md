# Platform-X — Testing Strategy

> How we test to ensure Excellence quality.

---

## 1. Testing Philosophy

- Test everything that can break.
- Tests are code — same quality standards.
- Tests run fast (< 5 min for full suite).
- Tests are deterministic (no flaky tests).
- Coverage target: 80%+ (Phase 2+).
- Every bug fix adds a test to prevent regression.

---

## 2. Test Pyramid

Unit tests (70%):
- Fast, isolated
- Test single functions/classes
- Mock external dependencies

Integration tests (20%):
- Test multiple components together
- Real database (test instance)
- Real HTTP calls (test server)

End-to-end tests (10%):
- Test critical flows from user perspective
- Browser automation
- Full stack

---

## 3. Backend Testing (pytest)

Unit tests:
- File: tests/unit/test_*.py
- Mock DB with fixtures
- Test business logic in isolation

Integration tests:
- File: tests/integration/test_*.py
- Use test database (separate from dev)
- Test API endpoints end-to-end

Fixtures (conftest.py):
- Test database
- Test client
- Test users
- Sample data
- Cleanup after each test

Coverage:
- Tool: pytest-cov
- Target: 80%+
- CI fails if coverage drops

---

## 4. Frontend Testing

Unit tests (JS):
- Tool: Vitest or Jest
- Test utility functions
- Test component logic

Integration tests:
- Tool: Testing Library
- Test component interactions

E2E tests:
- Tool: Playwright (preferred) or Cypress
- Test critical user flows:
  - Register → Login → Book room
  - Order food
  - Book spa
  - Redeem rewards

---

## 5. Test Database

- Separate from dev database
- Recreated before each test run
- Seeded with fixtures
- Uses SQLite for speed (or Postgres test container)

---

## 6. Test Data

Fixtures:
- test_user.json — standard user
- test_tenant.json — standard tenant
- test_booking.json — sample booking
- test_order.json — sample order

Factories:
- Use factory_boy for complex objects
- Realistic data generation

---

## 7. Continuous Testing

On every commit:
- Lint (ruff, black)
- Type check (mypy)
- Unit tests
- Integration tests

On PR:
- All above
- Coverage report
- E2E tests (subset)

Nightly:
- Full E2E suite
- Performance tests
- Security scans

---

## 8. Performance Testing

Tools:
- Locust or k6

Scenarios:
- 100 concurrent users (Phase 1)
- 1000 concurrent users (Phase 2)
- 10000 concurrent users (Phase 4)

Metrics:
- Response time (p95 < 500ms)
- Error rate (< 0.1%)
- Throughput (requests/sec)

---

## 9. Security Testing

Static analysis:
- bandit (Python)
- npm audit (JS)
- Semgrep

Dynamic:
- OWASP ZAP (automated scan)
- Manual pen testing (annually)

Specific tests:
- SQL injection attempts
- XSS payloads
- CSRF bypass attempts
- Auth bypass attempts
- Rate limit verification

---

## 10. Manual Testing

Before each release:
- Smoke tests on staging
- Test on real devices (iOS, Android)
- Test on slow network (throttled)
- Test with screen reader (accessibility)

---

## 11. Bug Reporting

Template:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, browser, version)
- Screenshots if applicable

Priority levels:
- P0: Production down
- P1: Critical feature broken
- P2: Major bug
- P3: Minor bug
- P4: Cosmetic

---

## 12. Regression Testing

- Every fixed bug gets a test
- Tests never deleted (only updated if requirements change)
- Regression suite runs on every commit

---

## 13. Definition of Done

A feature is done when:
- [ ] Code written
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] E2E test (if user-facing)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] Manually tested
- [ ] No regressions
- [ ] Committed with descriptive message

---

## 14. Testing Tools Summary

Backend:
- pytest
- pytest-cov
- pytest-asyncio
- httpx (test client)
- factory_boy

Frontend:
- Vitest or Jest
- Testing Library
- Playwright

Security:
- bandit
- Semgrep
- OWASP ZAP

Performance:
- Locust or k6

CI:
- GitHub Actions (or GitLab CI)

---

Last updated: September 2026
Status: Living document.
