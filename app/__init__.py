import os
from datetime import UTC, datetime

from flask import Flask, render_template

from app import models  # noqa: F401
from app.commands import register_commands
from app.config import config_by_name
from app.extensions import csrf, db, login_manager, migrate


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

    # Register custom CLI commands
    register_commands(app)

    # User loader required by Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.auth import User
        return db.session.get(User, int(user_id))

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

    # Global Template Context Processor
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user

        from app.models import Appointment, Invoice, Medicine, Owner, Pet

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

        return {
            'now': datetime.now(UTC),
            'recycle_bin_count': deleted_total
        }

    # Custom Error Handlers
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
