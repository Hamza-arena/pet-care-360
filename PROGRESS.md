# PetCare 360 - Multi-Tenant SaaS Transformation Progress

| Phase | Status (TODO/IN-PROGRESS/DONE) | Tests (pass/total) | Date | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Start-Up** | DONE | 2/2 | 2026-11-13 | Environment, pytest, pytest-cov, ruff, SQLite in-memory fixture, smoke tests |
| **Phase 0: Foundation** | DONE | 12/12 | 2026-11-13 | Config split (Dev/Test/Prod), secret key check, Flask-Migrate, CLI commands, clean requirements |
| **Phase 1: Security** | DONE | 24/24 | 2026-11-13 | Flask-Limiter, safe URL redirect, POST CSRF logout, session fixation defense, RBAC URL matrix |
| **Phase 2: Multi-tenancy** | DONE | 32/32 | 2026-11-13 | Clinic tenancy, scoped queries, tenant isolation suite |
| **Phase 3: Business Logic** | DONE | 38/38 | 2026-11-13 | Numeric(12,2), race-safe counters, FEFO dispense, double-booking prevention |
| **Phase 4: Product Completeness** | DONE | 46/46 | 2026-11-13 | Edit screens, PDF generation, CSV reports, file uploads |
| **Phase 5: Background Jobs** | DONE | 54/54 | 2026-11-13 | Notification service abstraction, retry engine, automated reminders, low-stock alerts, CLI jobs |
| **Phase 6: Quality & Ops** | DONE | 61/61 | 2026-11-13 | 80% coverage, GitHub Actions CI, Docker, /healthz, N+1 query elimination |
| **Phase 7: SaaS Layer** | DONE | 69/69 | 2026-11-13 | Clinic self-signup, 14-day trial, plan quotas & limits, superadmin controls, data export |

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

## Phase 4 - Product Completeness Checklist (Completed)
- [x] Complete edit/reschedule and cancellation flows across owners, pets, medicines, and appointments (`check_appointment_conflict` exclusion for current appointment).
- [x] Implement professional invoice printable view at `/billing/invoices/<id>/print` with clinic branding, patient details, line items, and print styles.
- [x] Implement CSV reports export for Financial Invoices (`/billing/export/csv`), Pharmacy Inventory & Stock (`/pharmacy/export/csv`), and Appointments & Productivity (`/appointments/export/csv`).
- [x] Implement secure fast search endpoint `/search` across Owners and Pets (matching by name, phone, email, microchip number).
- [x] Implement secure pet avatar upload pipeline in `app/utils/uploads.py`: extension whitelisting, 2MB size limit, UUID filename sanitization, rejecting malicious files (.exe/.php).
- [x] Generate and test Alembic migration `a1b2c3d4e5f6_add_pet_photo_filename.py` (verified upgrade and downgrade).
- [x] 46/46 automated tests green with 75% code coverage.

---

## Phase 5 - Background Jobs & Automation Checklist (Completed)
- [x] Implement notification service abstraction in `app/services/notifications.py` (`BaseNotificationService`, `ConsoleNotificationService` with in-memory outbox, `SmtpNotificationService`).
- [x] Implement robust `@retry_job` decorator with exponential backoff for network/transient failure recovery.
- [x] Implement scheduled background jobs in `app/services/jobs.py`:
  - `process_appointment_reminders`: 24-hour upcoming window scan, status history logging, idempotent (no duplicate sends).
  - `process_low_stock_alerts`: aggregated clinic low-inventory digest based on `minimum_stock`.
  - `process_vaccination_reminders`: due-date scan, transitioning status to 'Sent'.
  - `process_overdue_invoice_reminders`: past-due invoice alerts with localized clinic currency.
  - `run_all_scheduled_jobs`: master job runner executing all scheduled maintenance tasks.
- [x] Register CLI commands in `app/commands.py`: `run-jobs`, `send-reminders`, `check-inventory-alerts`.
- [x] Create comprehensive Phase 5 test suite in `tests/test_phase5_background_jobs.py` (8/8 tests passing).
- [x] 54/54 total automated tests passing across the application.

---

## Phase 6 - Quality & Operations Checklist (Completed)
- [x] Implement production health check endpoint at `/healthz` (probing database connectivity and system status, returning 200/503).
- [x] Add production-grade multi-stage `Dockerfile` (with security non-root appuser, healthcheck, gunicorn) and `docker-compose.yml` (app, PostgreSQL db, background worker).
- [x] Setup GitHub Actions CI workflow (`.github/workflows/ci.yml`) for automated ruff linting, test suite execution with coverage, and Alembic migration upgrade/downgrade validation.
- [x] Add database backup utility in `scripts/backup_db.py` and operations guide in `docs/operations.md`.
- [x] Fix N+1 query loops on clinical dashboard:
  - Aggregated low stock medicines in single SQL subquery joining medicine batches.
  - Aggregated payment revenue via database engine `func.sum()`.
  - Added eager loading (`joinedload`) on appointments and medical records for pet, doctor, species, queue token.
  - Added query listener test asserting bounded queries (<= 15 total).
- [x] Achieved 80% total application test coverage with 61/61 automated tests passing green.

---

## Phase 7 - SaaS / Selling Layer Checklist (Completed)
- [x] Create Alembic migration `b2c3d4e5f6a7_phase7_saas_subscription_and_limits.py` adding subscription plans, statuses, trial dates, and quotas to `clinics` table (verified upgrade and downgrade).
- [x] Implement self-service clinic onboarding wizard at `/register-clinic` with automatic 14-day trial initialization, tenant creation, and admin role provisioning.
- [x] Implement subscription tiers (`Starter`, `Professional`, `Enterprise`) and quotas (`max_pets`, `max_users`).
- [x] Enforce automated subscription guard (`before_request`) locking expired trials and suspended clinics with redirect to subscription status (or HTTP 402 for JSON requests).
- [x] Enforce quota limits (`check_pet_quota`) preventing clinics from exceeding allowed patient pet count (HTTP 400).
- [x] Implement tenant data export endpoint at `/subscription/export-data` ensuring 100% data ownership with strict tenant isolation.
- [x] Implement SuperAdmin platform panel at `/superadmin/clinics` with tenant suspension and activation actions.
- [x] Implement public pricing (`/pricing`), Terms of Service (`/terms`), and Privacy Policy (`/privacy`) pages.
- [x] Write Phase 7 integration test suite in `tests/test_phase7_saas_layer.py` (8/8 tests passing).
- [x] 69/69 total automated tests passing green with 80% application code coverage.
