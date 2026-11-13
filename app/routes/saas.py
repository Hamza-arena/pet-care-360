import json
try:
    from datetime import UTC, datetime, timedelta
except ImportError:
    from datetime import datetime, timedelta, timezone
    UTC = timezone.utc

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user

from app.extensions import db
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.finance import Invoice
from app.models.owners import Owner
from app.models.pets import Pet
from app.models.pharmacy import Medicine
from app.utils.decorators import admin_required
from app.utils.tenant import get_current_clinic, get_current_tenant_id, tenant_filter

saas_bp = Blueprint('saas', __name__)


PLAN_SPECS = {
    'Starter': {'max_pets': 100, 'max_users': 3, 'price_pkr': 5000},
    'Professional': {'max_pets': 1000, 'max_users': 10, 'price_pkr': 15000},
    'Enterprise': {'max_pets': 100000, 'max_users': 100, 'price_pkr': 35000},
}


@saas_bp.route('/pricing')
def pricing():
    return render_template('saas/pricing.html', plans=PLAN_SPECS)


@saas_bp.route('/terms')
def terms():
    return render_template('saas/terms.html')


@saas_bp.route('/privacy')
def privacy():
    return render_template('saas/privacy.html')


@saas_bp.route('/register-clinic', methods=['GET', 'POST'])
def register_clinic():
    """Self-service clinic signup wizard with 14-day trial initialization."""
    if request.method == 'POST':
        clinic_name = request.form.get('clinic_name', '').strip()
        city = request.form.get('city', '').strip()
        phone = request.form.get('phone', '').strip()
        clinic_email = request.form.get('clinic_email', '').strip().lower()

        username = request.form.get('admin_username', '').strip()
        email = request.form.get('admin_email', '').strip().lower()
        password = request.form.get('admin_password', '').strip()

        if not clinic_name or not username or not email or not password:
            flash('Please complete all required fields.', 'danger')
            return render_template('saas/register.html', plans=PLAN_SPECS)

        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash('A user with that email or username already exists.', 'warning')
            return render_template('saas/register.html', plans=PLAN_SPECS)

        # Initialize new Clinic with 14-day trial
        now = datetime.now(UTC)
        clinic = Clinic(
            name=clinic_name,
            city=city or 'Central',
            phone=phone or 'N/A',
            email=clinic_email or email,
            is_active=True,
            subscription_plan='Trial',
            subscription_status='trialing',
            trial_ends_at=now + timedelta(days=14),
            max_pets=100,
            max_users=3,
        )
        db.session.add(clinic)
        db.session.flush()

        # Ensure Admin role exists
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='Administrator')
            db.session.add(admin_role)
            db.session.flush()

        # Create clinic admin user
        user = User(
            clinic_id=clinic.id,
            email=email,
            username=username,
            first_name='Clinic',
            last_name='Admin',
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        ur = UserRole(user_id=user.id, role_id=admin_role.id)
        db.session.add(ur)
        db.session.commit()

        login_user(user)
        flash(f'Welcome to PetCare 360! Your 14-day trial for {clinic.name} has begun.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('saas/register.html', plans=PLAN_SPECS)


@saas_bp.route('/subscription/status')
@login_required
def subscription_status():
    """Overview of clinic subscription tier, expiration date, and quota utilization."""
    clinic = get_current_clinic()
    if not clinic:
        flash('No clinic associated with your account.', 'danger')
        return redirect(url_for('dashboard.index'))

    tenant_id = get_current_tenant_id()
    pet_count = tenant_filter(Pet.query_active(), Pet).count()
    user_count = User.query_active().filter(User.clinic_id == tenant_id).count()

    days_left = 0
    if clinic.subscription_status == 'trialing' and clinic.trial_ends_at:
        now = datetime.now(UTC)
        end = clinic.trial_ends_at if clinic.trial_ends_at.tzinfo else clinic.trial_ends_at.replace(tzinfo=UTC)
        days_left = max(0, (end - now).days)

    return render_template(
        'saas/subscription_status.html',
        clinic=clinic,
        pet_count=pet_count,
        user_count=user_count,
        days_left=days_left,
        plans=PLAN_SPECS,
    )


@saas_bp.route('/subscription/activate', methods=['POST'])
@login_required
@admin_required
def activate_subscription():
    """Upgrade or renew subscription plan."""
    clinic = get_current_clinic()
    plan_name = request.form.get('plan_name', 'Professional')

    spec = PLAN_SPECS.get(plan_name, PLAN_SPECS['Professional'])
    clinic.subscription_plan = plan_name
    clinic.subscription_status = 'active'
    clinic.max_pets = spec['max_pets']
    clinic.max_users = spec['max_users']
    clinic.subscription_ends_at = datetime.now(UTC) + timedelta(days=365)

    db.session.commit()
    flash(f'Successfully upgraded to {plan_name} plan! Your subscription is active for 1 year.', 'success')
    return redirect(url_for('saas.subscription_status'))


@saas_bp.route('/subscription/export-data')
@login_required
@admin_required
def export_clinic_data():
    """Allow clinic to download their entire tenant-scoped data in JSON format."""
    clinic = get_current_clinic()
    tenant_id = get_current_tenant_id()

    owners = tenant_filter(Owner.query_active(), Owner).all()
    pets = tenant_filter(Pet.query_active(), Pet).all()
    invoices = tenant_filter(Invoice.query_active(), Invoice).all()
    medicines = tenant_filter(Medicine.query_active(), Medicine).all()

    payload = {
        'clinic': {
            'id': clinic.id,
            'name': clinic.name,
            'email': clinic.email,
            'exported_at': datetime.now(UTC).isoformat(),
        },
        'owners': [
            {'id': o.id, 'name': f"{o.first_name} {o.last_name}", 'email': o.email, 'phone': o.phone}
            for o in owners
        ],
        'pets': [
            {'id': p.id, 'name': p.name, 'owner_id': p.owner_id, 'species': p.species.name if p.species else 'N/A'}
            for p in pets
        ],
        'invoices': [
            {'id': i.id, 'invoice_number': i.invoice_number, 'total': float(i.total_amount), 'status': i.status}
            for i in invoices
        ],
        'pharmacy_medicines': [
            {'id': m.id, 'name': m.name, 'unit': m.unit, 'minimum_stock': m.minimum_stock}
            for m in medicines
        ],
    }

    response = Response(
        json.dumps(payload, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename=petcare360_export_clinic_{tenant_id}.json'}
    )
    return response


@saas_bp.route('/superadmin/clinics')
@login_required
def superadmin_clinics():
    """Global Super-Admin control view for managing tenant states."""
    if not current_user.has_role('SuperAdmin'):
        return render_template('errors/403.html'), 403

    clinics = Clinic.query.order_by(Clinic.created_at.desc()).all()
    return render_template('saas/superadmin_clinics.html', clinics=clinics)


@saas_bp.route('/superadmin/clinics/<int:id>/toggle-status', methods=['POST'])
@login_required
def superadmin_toggle_status(id):
    """Super-Admin action to suspend or activate any clinic."""
    if not current_user.has_role('SuperAdmin'):
        return render_template('errors/403.html'), 403

    clinic = db.session.get(Clinic, id)
    if not clinic:
        return jsonify({'error': 'Clinic not found'}), 404

    action = request.form.get('action')
    if action == 'suspend':
        clinic.subscription_status = 'suspended'
        clinic.is_active = False
    elif action == 'activate':
        clinic.subscription_status = 'active'
        clinic.is_active = True
        clinic.subscription_ends_at = datetime.now(UTC) + timedelta(days=365)

    db.session.commit()
    flash(f"Clinic '{clinic.name}' status updated to {clinic.subscription_status}.", 'info')
    return redirect(url_for('saas.superadmin_clinics'))
