import os
from datetime import UTC, datetime

from flask import Flask, jsonify, render_template

from app import models  # noqa: F401
from app.commands import register_commands
from app.config import config_by_name
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    if isinstance(config_name, str):
        config_class = config_by_name.get(config_name, config_by_name['default'])
    else:
        config_class = config_name

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize configuration hooks
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register custom CLI commands
    register_commands(app)

    # User loader required by Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.auth import User
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # Register Blueprints
    from app.routes.admin import admin_bp
    from app.routes.appointments import appointments_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.finance import finance_bp
    from app.routes.laboratory import laboratory_bp
    from app.routes.medical import medical_bp
    from app.routes.owners import owners_bp
    from app.routes.pets import pets_bp
    from app.routes.pharmacy import pharmacy_bp
    from app.routes.saas import saas_bp
    from app.routes.vaccination import vaccination_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(owners_bp)
    app.register_blueprint(pets_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(laboratory_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(vaccination_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(saas_bp)

    # Global Template Context Processor
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user

        from app.models import Appointment, Invoice, Medicine, Owner, Pet
        from app.utils.tenant import get_current_clinic

        deleted_total = 0
        if current_user.is_authenticated and current_user.has_role('Admin'):
            try:
                deleted_total = (
                    Pet.query_deleted().count() +
                    Owner.query_deleted().count() +
                    Appointment.query_deleted().count() +
                    Medicine.query_deleted().count() +
                    Invoice.query_deleted().count()
                )
            except Exception:  # noqa: BLE001
                deleted_total = 0

        clinic = get_current_clinic()
        return {
            'now': datetime.now(UTC),
            'recycle_bin_count': deleted_total,
            'current_clinic': clinic,
            'currency': (clinic.currency if clinic and getattr(clinic, 'currency', None) else 'PKR'),
        }

    # Sentry error monitoring integration (if DSN provided in environment)
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.2,
            )
        except ImportError:
            pass

    # Tenant Subscription Access Guard (Phase 7 SaaS)
    @app.before_request
    def check_tenant_subscription():
        from flask import flash, jsonify, redirect, request, url_for
        from flask_login import current_user

        from app.utils.tenant import get_current_clinic

        if not current_user.is_authenticated:
            return None

        endpoint = request.endpoint or ''
        if endpoint.startswith(('auth.', 'saas.', 'static')) or endpoint == 'health_check':
            return None

        if current_user.has_role('SuperAdmin'):
            return None

        clinic = get_current_clinic()
        if clinic and not clinic.is_subscription_active():
            is_json = request.is_json or 'application/json' in request.headers.get('Accept', '')
            if is_json:
                return jsonify({
                    'error': 'Subscription Expired',
                    'message': 'Your clinic subscription has expired or is suspended.',
                    'status': clinic.subscription_status,
                }), 402
            flash('Your clinic subscription or trial has expired. Please upgrade or renew your plan to continue.', 'warning')
            return redirect(url_for('saas.subscription_status'))

        return None

    # Public Health Endpoint for load balancers and orchestrators
    @app.route('/healthz')
    def health_check():
        """Comprehensive health check endpoint probing database connectivity."""
        try:
            db.session.execute(db.text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now(UTC).isoformat(),
            }), 200
        except Exception as e:  # noqa: BLE001
            return jsonify({
                'status': 'unhealthy',
                'database': 'error',
                'error': str(e),
                'timestamp': datetime.now(UTC).isoformat(),
            }), 503

    # Template Currency Filter
    @app.template_filter('currency')
    def currency_filter(val):
        if val is None:
            val = 0.0
        from app.utils.tenant import get_current_clinic
        clinic = get_current_clinic()
        curr = clinic.currency if clinic and getattr(clinic, 'currency', None) else 'PKR'
        return f"{curr} {float(val):,.2f}"

    # Custom Error Handlers
    @app.errorhandler(429)
    def ratelimit_exceeded(e):
        return render_template('errors/429.html', error=e), 429

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
