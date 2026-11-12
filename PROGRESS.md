# PetCare 360 - Multi-Tenant SaaS Transformation Progress

| Phase | Status (TODO/IN-PROGRESS/DONE) | Tests (pass/total) | Date | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Start-Up** | DONE | 2/2 | 2026-11-13 | Environment, pytest, pytest-cov, ruff, SQLite in-memory fixture, smoke tests |
| **Phase 0: Foundation** | DONE | 12/12 | 2026-11-13 | Config split (Dev/Test/Prod), secret key check, Flask-Migrate, CLI commands, clean requirements |
| **Phase 1: Security** | TODO | - | - | Rate limiting, safe redirect, CSRF logout, secure sessions, RBAC URL matrix |
| **Phase 2: Multi-tenancy** | TODO | - | - | Clinic tenancy, scoped queries, tenant isolation suite |
| **Phase 3: Business Logic** | TODO | - | - | Numeric(12,2), race-safe counters, FEFO dispense, double-booking prevention |
| **Phase 4: Product Completeness** | TODO | - | - | Edit screens, PDF generation, CSV reports, file uploads |
| **Phase 5: Background Jobs** | TODO | - | - | Celery/Redis, automated reminders, inventory alerts |
| **Phase 6: Quality & Ops** | TODO | - | - | 80%+ coverage, GitHub Actions CI, Docker, /healthz, N+1 query optimization |
| **Phase 7: SaaS Layer** | TODO | - | - | Clinic signup, plans, subscription tracking, super-admin panel |

---

## Phase 0 - Foundation Checklist (Completed)
- [x] Split `app/config.py` into `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`.
- [x] Enforce that in `ProductionConfig`, missing/insecure `SECRET_KEY` raises a fatal error (no default fallback).
- [x] Ensure `FLASK_DEBUG` is disabled in production.
- [x] Restrict `/auth/demo-login` so it is only available when `app.config['TESTING']` or `app.config['DEBUG']` is True (returns 404 in production).
- [x] Remove `seed.py` from `build.sh` (replace with `flask db upgrade`).
- [x] Create `flask create-admin` CLI command prompting for username, email, and password securely.
- [x] Create `flask seed-demo` CLI command for dev demo data.
- [x] Setup `Flask-Migrate` (`flask db init` and generate initial migration), test `upgrade` and `downgrade`.
- [x] Clean `requirements.txt`: pin versions, standardize on `psycopg` driver.
- [x] Create `.env.example` with clear documentation.
- [x] Update `README.md` (setup, env vars, running, testing, Render deployment).
- [x] Write automated tests for all Phase 0 Exit Criteria in `tests/test_phase0.py`.

---

## Phase 1 - Security Checklist (Next Phase)
- [ ] Install and configure `Flask-Limiter` (rate limiting on `/auth/login` - e.g. 5/min, 20/hour).
- [ ] Safe `next` redirect validation helper using `urllib.parse.urlsplit` to prevent Open Redirect vulnerabilities.
- [ ] Change `/auth/logout` from GET to POST with CSRF validation.
- [ ] Configure secure cookies (`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE=True` in Prod).
- [ ] Session fixation defense: regenerate session on successful login.
- [ ] Role-Based Access Control (RBAC) URL matrix enforcement: test matrix verifying unauthenticated/unauthorized access across all endpoints.
