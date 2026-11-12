from flask import abort, session
from flask_login import current_user

from app.extensions import db
from app.models.clinic import Clinic


def get_current_tenant_id() -> int | None:
    """Resolve the active clinic (tenant) ID for the current request context."""
    if not current_user or not current_user.is_authenticated:
        return session.get('active_clinic_id')

    # If the user explicitly switched clinics via session, respect that
    active_in_session = session.get('active_clinic_id')
    if active_in_session:
        return active_in_session

    # Otherwise return the user's assigned clinic_id
    return getattr(current_user, 'clinic_id', None)


def get_current_clinic() -> Clinic | None:
    """Return the Clinic model instance for the active tenant."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return None
    return db.session.get(Clinic, tenant_id)


def tenant_filter(query, model):
    """Scope a query to the current active tenant clinic.

    Superadmins without an active clinic selection see all records.
    Tenant-bound users only see records belonging to their clinic.
    """
    tenant_id = get_current_tenant_id()

    # If user is Admin with no clinic constraint, don't filter
    if current_user and current_user.is_authenticated and current_user.has_role('Admin') and not tenant_id:
        return query

    if not tenant_id:
        return query

    # Direct clinic_id attribute
    if hasattr(model, 'clinic_id'):
        return query.filter(model.clinic_id == tenant_id)

    # Pet model scopes through Owner
    if model.__name__ == 'Pet':
        from app.models.owners import Owner
        return query.join(Owner, model.owner_id == Owner.id).filter(Owner.clinic_id == tenant_id)

    return query


def assert_tenant_access(record, error_code=404):
    """Enforce tenant isolation on a specific record instance.

    Aborts with 404 (or 403) if the record belongs to another clinic.
    """
    if record is None:
        abort(404)

    tenant_id = get_current_tenant_id()

    # Superadmin with no specific clinic filter has global visibility
    if (
        current_user
        and current_user.is_authenticated
        and current_user.has_role('Admin')
        and not getattr(current_user, 'clinic_id', None)
        and not session.get('active_clinic_id')
    ):
        return record

    if not tenant_id:
        return record

    # Check direct clinic_id
    if hasattr(record, 'clinic_id') and record.clinic_id is not None and record.clinic_id != tenant_id:
        abort(error_code)

    # Check pet through owner
    if (
        hasattr(record, 'owner')
        and record.owner is not None
        and hasattr(record.owner, 'clinic_id')
        and record.owner.clinic_id is not None
        and record.owner.clinic_id != tenant_id
    ):
        abort(error_code)

    return record

