from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Decorator ensuring current user has at least one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not any(current_user.has_role(r) for r in roles):
                flash('Access denied. You do not have permission to view this resource.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required('Admin')(f)


def doctor_required(f):
    return role_required('Admin', 'Doctor')(f)


def staff_required(f):
    return role_required('Admin', 'Doctor', 'Nurse', 'Receptionist', 'Pharmacist')(f)

