import os

import pytest

from app import create_app
from app.commands import create_admin_command
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.extensions import db
from app.models.auth import User


def test_development_config():
    assert DevelopmentConfig.DEBUG is True
    assert DevelopmentConfig.TESTING is False
    assert DevelopmentConfig.WTF_CSRF_ENABLED is True


def test_testing_config():
    assert TestingConfig.DEBUG is False
    assert TestingConfig.TESTING is True
    assert TestingConfig.WTF_CSRF_ENABLED is False


def test_production_config_rejects_missing_secret_key(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db')
    with pytest.raises(RuntimeError, match="SECRET_KEY environment variable MUST be explicitly set"):
        app = create_app(ProductionConfig)
        with app.app_context():
            pass


def test_production_config_rejects_default_dev_secret_key(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'dev-insecure-key')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db')
    with pytest.raises(RuntimeError, match="SECRET_KEY environment variable MUST be explicitly set"):
        app = create_app(ProductionConfig)
        with app.app_context():
            pass


def test_production_config_rejects_missing_database_url(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'super-secure-production-random-secret-key-999')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL environment variable is required"):
        app = create_app(ProductionConfig)
        with app.app_context():
            pass


def test_demo_login_allowed_in_testing(client, app):
    """In testing mode, demo login is active."""
    with app.app_context():
        # Ensure a demo admin exists
        admin = User.query.filter_by(email='admin@petcare360.com').first()
        if not admin:
            admin = User(
                email='admin@petcare360.com',
                username='admin',
                first_name='Admin',
                last_name='User'
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()

    resp = client.get('/auth/demo-login/admin')
    assert resp.status_code == 302
    assert resp.headers.get('Location') in ['/', 'http://localhost/']


def test_demo_login_forbidden_in_production(app):
    """In production mode (DEBUG=False, TESTING=False), /auth/demo-login must return 404."""
    # Temporarily disable TESTING
    app.config['TESTING'] = False
    app.config['DEBUG'] = False
    try:
        client = app.test_client()
        resp = client.get('/auth/demo-login/admin')
        assert resp.status_code == 404
    finally:
        app.config['TESTING'] = True


def test_create_admin_cli(runner, app):
    """Test flask create-admin command."""
    with app.app_context():
        # Clean existing test admin if any
        User.query.filter_by(email='newadmin@petcare.com').delete()
        db.session.commit()

    result = runner.invoke(
        create_admin_command,
        input='newadmin@petcare.com\nnewadmin\nAlice\nSmith\nSecurePass123!\nSecurePass123!\n'
    )
    assert result.exit_code == 0
    assert 'configured successfully' in result.output

    with app.app_context():
        user = User.query.filter_by(email='newadmin@petcare.com').first()
        assert user is not None
        assert user.username == 'newadmin'
        assert user.first_name == 'Alice'
        assert user.check_password('SecurePass123!') is True
        assert user.has_role('Admin') is True


def test_migrations_folder_exists():
    assert os.path.isdir('migrations')
    assert os.path.isdir('migrations/versions')
    versions = os.listdir('migrations/versions')
    migration_files = [f for f in versions if f.endswith('.py') and not f.startswith('__')]
    assert len(migration_files) >= 1


def test_migrations_upgrade_and_downgrade(tmp_path):
    """Verify that Alembic migrations run upgrade and downgrade cleanly on an empty SQLite database."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    test_db = tmp_path / "test_migration.db"
    db_uri = f"sqlite:///{test_db}"

    class BlankMigrationConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = db_uri

    blank_app = create_app(BlankMigrationConfig)
    with blank_app.app_context():
        alembic_cfg = AlembicConfig("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")

        # Upgrade to head (creates all tables)
        command.upgrade(alembic_cfg, "head")

        # Downgrade to base (drops all tables)
        command.downgrade(alembic_cfg, "base")

