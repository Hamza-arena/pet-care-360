from datetime import UTC, datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms.auth import LoginForm
from app.models.audit import log_activity
from app.models.auth import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
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
            login_user(user, remember=form.remember_me.data)
            log_activity('LOGIN', 'User', user.id, f'User {user.username} logged in successfully.')
            db.session.commit()

            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password. Please check your credentials.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_activity('LOGOUT', 'User', current_user.id, f'User {current_user.username} logged out.')
    db.session.commit()
    logout_user()
    flash('You have been signed out safely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/demo-login/<role_name>')
def demo_login(role_name):
    """Convenient 1-click account switcher for testing/development only. Disabled in production."""
    if not (current_app.config.get('DEBUG') or current_app.config.get('TESTING')):
        abort(404)

    role_email_map = {
        'admin': 'admin@petcare360.com',
        'doctor': 'doctor@petcare360.com',
        'staff': 'staff@petcare360.com',
        'receptionist': 'staff@petcare360.com'
    }
    target_email = role_email_map.get(role_name.lower())
    if target_email:
        user = User.query.filter_by(email=target_email).first()
        if user:
            login_user(user)
            flash(f'Switched session to {user.first_name} ({role_name.capitalize()} Mode)', 'success')
            return redirect(url_for('dashboard.index'))

    flash(f'Demo user for {role_name} not found. Please run seed script.', 'warning')
    return redirect(url_for('auth.login'))

