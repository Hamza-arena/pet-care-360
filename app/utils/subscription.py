from functools import wraps

from flask import abort, flash, jsonify, redirect, request, url_for
from flask_login import current_user

from app.utils.tenant import get_current_clinic


def subscription_required(fn):
    """Decorator ensuring that the active tenant has an active, valid subscription or trial.

    SuperAdmin users bypass subscription restrictions.
    """
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return fn(*args, **kwargs)

        if current_user.has_role('SuperAdmin'):
            return fn(*args, **kwargs)

        clinic = get_current_clinic()
        if clinic and not clinic.is_subscription_active():
            if request.is_json:
                return jsonify({
                    'error': 'Subscription Required',
                    'message': 'Your clinic subscription or trial has expired or is suspended.',
                    'status': clinic.subscription_status,
                }), 402

            flash('Your clinic subscription or trial has expired. Please upgrade or renew your plan to continue.', 'warning')
            return redirect(url_for('saas.subscription_status'))

        return fn(*args, **kwargs)
    return decorated_view


def check_pet_quota(clinic, current_count):
    """Raise HTTP 400 if clinic has reached its allowed pet limit."""
    if clinic and not clinic.can_add_pet(current_count):
        abort(400, description=f"Plan limit reached: your {clinic.subscription_plan} plan permits up to {clinic.max_pets} pets.")


def check_user_quota(clinic, current_count):
    """Raise HTTP 400 if clinic has reached its allowed user limit."""
    if clinic and not clinic.can_add_user(current_count):
        abort(400, description=f"Plan limit reached: your {clinic.subscription_plan} plan permits up to {clinic.max_users} users.")

