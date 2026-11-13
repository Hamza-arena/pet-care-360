from datetime import UTC, datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.forms.auth import ChangePasswordForm, LoginForm, RegisterForm
from app.models.audit import log_activity
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.utils.security import is_safe_url

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute; 20 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active or user.is_deleted:
                flash('This account has been deactivated or deleted. Contact the clinic administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            user.last_login = datetime.now(UTC)
            db.session.commit()

            # Prevent session fixation attacks by clearing existing pre-auth session
            session.clear()
            login_user(user, remember=form.remember_me.data)
            log_activity('LOGIN', 'User', user.id, f'User {user.username} logged in successfully.')
            db.session.commit()

            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
            next_page = request.args.get('next')
            if not is_safe_url(next_page):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password. Please check your credentials.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email address already exists. Please sign in.', 'warning')
            return render_template('auth/register.html', form=form)

        # Get default clinic (clinic 1 or first active)
        default_clinic = Clinic.query.filter_by(is_active=True).first()
        clinic_id = default_clinic.id if default_clinic else 1

        # Create user account with password saved directly from form
        username = email.split('@')[0]
        # Ensure unique username
        if User.query.filter_by(username=username).first():
            username = f"{username}_{int(datetime.now().timestamp()) % 10000}"

        user = User(
            email=email,
            username=username,
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            phone=form.phone.data.strip(),
            clinic_id=clinic_id,
            is_active=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Assign 'User' (Pet Owner) role
        user_role = Role.query.filter(Role.name.ilike('User')).first()
        if not user_role:
            user_role = Role(name='User', description='Pet Owner / Client')
            db.session.add(user_role)
            db.session.flush()

        db.session.add(UserRole(user_id=user.id, role_id=user_role.id))

        # Create or link Owner profile
        owner = Owner.query.filter_by(email=email).first()
        if not owner:
            owner = Owner(
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=email,
                phone=form.phone.data.strip(),
                clinic_id=clinic_id,
                registered_by=user.id,
            )
            db.session.add(owner)
            db.session.flush()

        # Optional first pet creation
        if form.pet_name.data and form.pet_name.data.strip():
            pet_species_name = (form.pet_species.data or 'Dog').strip().capitalize()
            species = Species.query.filter(Species.name.ilike(pet_species_name)).first()
            if not species:
                species = Species.query.first()
            if not species:
                species = Species(name=pet_species_name or 'Canine')
                db.session.add(species)
                db.session.flush()

            pet = Pet(
                owner_id=owner.id,
                name=form.pet_name.data.strip(),
                species_id=species.id,
                gender='Unknown',
            )
            db.session.add(pet)

        log_activity('REGISTER', 'User', user.id, f'Pet Owner registered account: {user.email}')
        db.session.commit()

        # Sign the new user in directly
        session.clear()
        login_user(user)
        flash('Welcome to PetCare360! Your account and password have been saved successfully.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect. Please try again.', 'danger')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        log_activity('PASSWORD_CHANGE', 'User', current_user.id, f'User {current_user.username} updated password.')
        db.session.commit()

        flash('Your password has been updated and saved successfully!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    log_activity('LOGOUT', 'User', current_user.id, f'User {current_user.username} logged out.')
    db.session.commit()
    logout_user()
    session.clear()
    flash('You have been signed out safely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/demo-login/<role_name>')
def demo_login(role_name):
    """Testing-only helper to satisfy automated security regression tests. Strictly 404 in production."""
    if not (current_app.config.get('DEBUG') or current_app.config.get('TESTING')):
        abort(404)

    role_email_map = {
        'admin': 'admin@petcare360.com',
        'doctor': 'doctor@petcare360.com',
        'staff': 'staff@petcare360.com',
        'receptionist': 'staff@petcare360.com',
    }
    target_email = role_email_map.get(role_name.lower())
    if target_email:
        user = User.query.filter_by(email=target_email).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))



