import pytest

from app import create_app
from app.extensions import db
from app.models.auth import Role, User, UserRole


class TestingConfig:
    TESTING = True
    SECRET_KEY = 'test-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    ITEMS_PER_PAGE = 10


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client, app):
    """Client authenticated as a default test admin user."""
    with app.app_context():
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='Administrator')
            db.session.add(admin_role)
            db.session.commit()

        user = User(
            email='testadmin@petcare360.com',
            username='testadmin',
            first_name='Test',
            last_name='Admin',
            is_active=True
        )
        user.set_password('Admin@123')
        db.session.add(user)
        db.session.commit()

        db.session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.session.commit()
        user_id = str(user.id)

    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
        sess['_fresh'] = True

    return client


@pytest.fixture
def doctor_client(app):
    """Client authenticated as a Doctor."""
    client = app.test_client()
    with app.app_context():
        doc_role = Role.query.filter_by(name='Doctor').first()
        if not doc_role:
            doc_role = Role(name='Doctor', description='Veterinarian')
            db.session.add(doc_role)
            db.session.commit()

        user = User.query.filter_by(email='testdoctor@petcare360.com').first()
        if not user:
            user = User(
                email='testdoctor@petcare360.com',
                username='testdoctor',
                first_name='Test',
                last_name='Doctor',
                is_active=True
            )
            user.set_password('Doctor@123')
            db.session.add(user)
            db.session.commit()
            db.session.add(UserRole(user_id=user.id, role_id=doc_role.id))
            db.session.commit()
        user_id = str(user.id)

    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
        sess['_fresh'] = True

    return client


@pytest.fixture
def receptionist_client(app):
    """Client authenticated as a Receptionist (Staff)."""
    client = app.test_client()
    with app.app_context():
        rec_role = Role.query.filter_by(name='Receptionist').first()
        if not rec_role:
            rec_role = Role(name='Receptionist', description='Front desk')
            db.session.add(rec_role)
            db.session.commit()

        user = User.query.filter_by(email='testreceptionist@petcare360.com').first()
        if not user:
            user = User(
                email='testreceptionist@petcare360.com',
                username='testreceptionist',
                first_name='Test',
                last_name='Receptionist',
                is_active=True
            )
            user.set_password('Staff@123')
            db.session.add(user)
            db.session.commit()
            db.session.add(UserRole(user_id=user.id, role_id=rec_role.id))
            db.session.commit()
        user_id = str(user.id)

    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
        sess['_fresh'] = True

    return client

