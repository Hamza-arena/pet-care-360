# PetCare 360 - Multi-Tenant SaaS Transformation Progress

| Phase | Status (TODO/IN-PROGRESS/DONE) | Tests (pass/total) | Date | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Start-Up** | DONE | 2/2 | 2026-11-13 | Environment, pytest, pytest-cov, ruff, SQLite in-memory fixture, smoke tests |
| **Phase 0: Foundation** | DONE | 12/12 | 2026-11-13 | Config split (Dev/Test/Prod), secret key check, Flask-Migrate, CLI commands, clean requirements |
| **Phase 1: Security** | DONE | 24/24 | 2026-11-13 | Flask-Limiter, safe URL redirect, POST CSRF logout, session fixation defense, RBAC URL matrix |
| **Phase 2: Multi-tenancy** | DONE | 32/32 | 2026-11-13 | Clinic tenancy, scoped queries, tenant isolation suite |
| **Phase 3: Business Logic** | DONE | 38/38 | 2026-11-13 | Numeric(12,2), race-safe counters, FEFO dispense, double-booking prevention |
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

## Phase 1 - Security Checklist (Completed)
- [x] Install and configure `Flask-Limiter` (rate limiting on `/auth/login`: 5/min, 20/hour).
- [x] Safe `next` redirect validation helper using `urllib.parse.urlsplit` in `app/utils/security.py` to prevent Open Redirect vulnerabilities.
- [x] Change `/auth/logout` from GET to POST with CSRF validation.
- [x] Update navbar and profile templates to submit logout via POST form with CSRF token.
- [x] Configure secure cookies (`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE=True` in Prod).
- [x] Session fixation defense: regenerate/clear session on successful login before `login_user()`.
- [x] Role-Based Access Control (RBAC) URL matrix enforcement test suite verifying Anonymous, Receptionist, Doctor, and Admin access.

---

## Phase 2 - Multi-tenancy Checklist (Completed)
- [x] Implement `TenantMixin` in `app/models/base.py` and assign `clinic_id` foreign keys to User, Owner, Medicine, Invoice, LabOrder, MedicalRecord.
- [x] Generate and test Alembic migration `0de89771a5af_add_multitenancy_clinic_id.py` with explicit batch constraint names for SQLite compatibility; verify both upgrade and downgrade.
- [x] Implement tenant resolution helpers in `app/utils/tenant.py`: `get_current_tenant_id()`, `tenant_filter()`, and `assert_tenant_access()`.
- [x] Protect routes across owners, pets, appointments, medical records, laboratory, pharmacy, and billing with strict tenant filtering and assertions.
- [x] Create comprehensive Tenant Isolation test suite in `tests/test_phase2_multitenancy.py` (verifying cross-clinic 404s, list scoping, and superadmin global view).
- [x] 32/32 tests green with 71% overall code coverage.

---

## Phase 3 - Business Logic Checklist (Completed)
- [x] Convert Float money columns to `Numeric(12, 2)` across `Invoice`, `InvoiceItem`, `Payment`, `Medicine`, `MedicineBatch`, `LabTest`, `AppointmentType`.
- [x] Add `currency` (default PKR), `tax_rate` (16.00%), and `invoice_sequence` to `Clinic` model.
- [x] Implement dynamic `currency` Jinja filter and context processor, replacing all hardcoded `$` signs with PKR/clinic setting across forms, routes, flash messages, and templates.
- [x] Implement race-safe sequential invoice numbering using atomic SQL `UPDATE ... RETURNING` in `app/utils/finance.py`.
- [x] Implement server-side penny-accurate Decimal calculations for subtotal, tax_amount, discount, total, and balance in `recalculate_invoice`.
- [x] Implement First-Expired, First-Out (FEFO) automated dispensing and strict expiration date rejection (HTTP 400) in `app/routes/pharmacy.py`.
- [x] Implement double-booking conflict validation for doctors and rooms in `app/utils/appointments.py` (HTTP 400 on overlap).
- [x] Wrap clinical examination, diagnosis, and treatment creation in atomic database transaction in `app/routes/medical.py`.
- [x] Create and verify Alembic migration `5e1b2c3d4f5a` (tested with upgrade and downgrade).
- [x] 38/38 automated tests green with 73% code coverage.

---

## Phase 4 - Product Completeness Checklist (Next Phase)
- [ ] Implement missing Edit/Update forms and routes (Edit Owner, Edit Pet, Edit Medicine, Edit Appointment).
- [ ] Implement invoice PDF download generation (WeasyPrint / ReportLab / HTML-to-PDF).
- [ ] Implement CSV export for financial summaries, appointment logs, and pharmacy inventory.
- [ ] Implement secure pet profile photo and medical record attachment file uploads (allowed extensions, file size validation, random filename hashing).
- [ ] Write integration test suite verifying edit workflows, CSV downloads, PDF generation, and upload validation in `tests/test_phase4_product_completeness.py`.
