from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.owners import Owner
from app.models.pets import Pet, Species


def test_migrations_phase7_upgrade_and_downgrade(tmp_path):
    """Verify that Alembic can cleanly upgrade to Phase 7 (SaaS subscription) and downgrade back."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app import create_app
    from app.config import TestingConfig

    test_db = tmp_path / "test_p7_migration.db"
    db_uri = f"sqlite:///{test_db}"

    class BlankMigrationConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = db_uri

    blank_app = create_app(BlankMigrationConfig)
    with blank_app.app_context():
        alembic_cfg = AlembicConfig("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")

        # Upgrade to head (Phase 7)
        command.upgrade(alembic_cfg, 'head')
        # Downgrade to Phase 4
        command.downgrade(alembic_cfg, 'a1b2c3d4e5f6')
        # Re-upgrade to head
        command.upgrade(alembic_cfg, 'head')


def test_public_saas_pages(client):
    """Verify public pricing, terms, and privacy pages are accessible without login."""
    assert client.get('/pricing').status_code == 200
    assert client.get('/terms').status_code == 200
    assert client.get('/privacy').status_code == 200


def test_clinic_self_signup_and_trial_initialization(client, app):
    """Verify clinic self-signup wizard initializes 14-day trial and logs in clinic admin."""
    res = client.get('/register-clinic')
    assert res.status_code == 200

    res = client.post('/register-clinic', data={
        'clinic_name': 'Islamabad Animal Hospital',
        'city': 'Islamabad',
        'phone': '0511234567',
        'clinic_email': 'info@isbvet.com',
        'admin_username': 'isb_admin',
        'admin_email': 'admin@isbvet.com',
        'admin_password': 'AdminSecurePassword123!',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        clinic = Clinic.query.filter_by(name='Islamabad Animal Hospital').first()
        assert clinic is not None
        assert clinic.subscription_plan == 'Trial'
        assert clinic.subscription_status == 'trialing'
        assert clinic.trial_ends_at is not None
        trial_end = clinic.trial_ends_at if clinic.trial_ends_at.tzinfo else clinic.trial_ends_at.replace(tzinfo=UTC)
        assert trial_end > datetime.now(UTC)
        assert clinic.max_pets == 100
        assert clinic.max_users == 3

        admin_user = User.query.filter_by(email='admin@isbvet.com').first()
        assert admin_user is not None
        assert admin_user.clinic_id == clinic.id
        assert admin_user.has_role('Admin')


def test_expired_subscription_locks_clinic(client, app):
    """Verify that an expired trial or subscription locks access and redirects to subscription page."""
    with app.app_context():
        now = datetime.now(UTC)
        clinic = Clinic(
            name='Expired Clinic',
            subscription_plan='Trial',
            subscription_status='trialing',
            trial_ends_at=now - timedelta(days=2),  # expired 2 days ago
            is_active=True,
        )
        role = Role(name='Receptionist')
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username='exp_user', email='exp@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
        db.session.commit()

    # Login
    client.post('/auth/login', data={'email': 'exp@test.com', 'password': 'Pass123!'})

    # Accessing regular dashboard should redirect to subscription status
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/subscription/status' in res.headers['Location']

    # JSON API call receives 402 Payment Required
    res_json = client.get('/', headers={'Accept': 'application/json'})
    assert res_json.status_code == 402
    data = res_json.get_json()
    assert data['error'] == 'Subscription Expired'


def test_plan_activation_restores_access(client, app):
    """Verify activating or upgrading subscription unlocks clinic access."""
    with app.app_context():
        now = datetime.now(UTC)
        clinic = Clinic(
            name='Renewable Clinic',
            subscription_plan='Trial',
            subscription_status='expired',
            trial_ends_at=now - timedelta(days=5),
            is_active=True,
        )
        admin_role = Role(name='Admin')
        db.session.add_all([clinic, admin_role])
        db.session.flush()

        user = User(username='renew_user', email='renew@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.session.commit()
        clinic_id = clinic.id

    client.post('/auth/login', data={'email': 'renew@test.com', 'password': 'Pass123!'})

    # Activate Professional plan
    res = client.post('/subscription/activate', data={'plan_name': 'Professional'}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated_clinic = db.session.get(Clinic, clinic_id)
        assert updated_clinic.subscription_plan == 'Professional'
        assert updated_clinic.subscription_status == 'active'
        assert updated_clinic.max_pets == 1000
        assert updated_clinic.max_users == 10
        assert updated_clinic.is_subscription_active() is True

    # Now accessing regular clinical dashboard succeeds
    res_dash = client.get('/')
    assert res_dash.status_code == 200


def test_pet_quota_limit_enforcement(client, app):
    """Verify that attempting to exceed plan pet quota raises HTTP 400."""
    with app.app_context():
        clinic = Clinic(
            name='Quota Clinic',
            subscription_plan='Starter',
            subscription_status='active',
            max_pets=1,  # limit to exactly 1 pet
            is_active=True,
        )
        role = Role(name='Receptionist')
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username='quota_user', email='quota@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        owner = Owner(clinic_id=clinic.id, first_name='Amir', last_name='Liaquat', phone='03001230000')
        species = Species(name='Feline-Quota')
        db.session.add_all([owner, species])
        db.session.flush()

        # Add 1st pet (reaching quota limit 1)
        p1 = Pet(owner_id=owner.id, species_id=species.id, name='ExistingCat')
        db.session.add(p1)
        db.session.commit()
        owner_id = owner.id
        species_id = species.id

    client.post('/auth/login', data={'email': 'quota@test.com', 'password': 'Pass123!'})

    # Attempting to add 2nd pet should exceed quota and abort with 400
    res = client.post('/pets/new', data={
        'name': 'OverLimitCat',
        'owner_id': owner_id,
        'species_id': species_id,
        'gender': 'Male',
    })
    assert res.status_code == 400
    assert b'Plan limit reached' in res.data


def test_tenant_data_export_isolation(client, app):
    """Verify that clinic data export downloads only that clinic's data and not other tenants'."""
    with app.app_context():
        c1 = Clinic(name='Export Clinic A', subscription_plan='Professional', subscription_status='active', is_active=True)
        c2 = Clinic(name='Export Clinic B', subscription_plan='Professional', subscription_status='active', is_active=True)
        admin_role = Role(name='Admin')
        db.session.add_all([c1, c2, admin_role])
        db.session.flush()

        u1 = User(username='u1_export', email='u1_export@test.com', clinic_id=c1.id, is_active=True)
        u1.set_password('Pass123!')
        u2 = User(username='u2_export', email='u2_export@test.com', clinic_id=c2.id, is_active=True)
        u2.set_password('Pass123!')
        db.session.add_all([u1, u2])
        db.session.flush()
        db.session.add_all([
            UserRole(user_id=u1.id, role_id=admin_role.id),
            UserRole(user_id=u2.id, role_id=admin_role.id),
        ])

        o1 = Owner(clinic_id=c1.id, first_name='Tariq', last_name='Alpha', phone='03001111111', email='tariq@alpha.com')
        o2 = Owner(clinic_id=c2.id, first_name='Javed', last_name='Beta', phone='03002222222', email='javed@beta.com')
        db.session.add_all([o1, o2])
        db.session.commit()

    # Log in as Clinic A
    client.post('/auth/login', data={'email': 'u1_export@test.com', 'password': 'Pass123!'})

    res = client.get('/subscription/export-data')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/json'

    data = res.get_json()
    assert data['clinic']['name'] == 'Export Clinic A'
    exported_owner_names = [o['name'] for o in data['owners']]
    assert 'Tariq Alpha' in exported_owner_names
    assert 'Javed Beta' not in exported_owner_names  # Cross-tenant data isolation verified


def test_superadmin_controls(client, app):
    """Verify SuperAdmin can view all clinics and suspend/activate tenant accounts."""
    with app.app_context():
        c = Clinic(name='Target Clinic', subscription_plan='Starter', subscription_status='active', is_active=True)
        super_role = Role(name='SuperAdmin')
        staff_role = Role(name='Receptionist')
        db.session.add_all([c, super_role, staff_role])
        db.session.flush()

        regular_user = User(username='regular_guy', email='regular@test.com', clinic_id=c.id, is_active=True)
        regular_user.set_password('Pass123!')
        super_user = User(username='super_admin', email='super@petcare360.com', clinic_id=c.id, is_active=True)
        super_user.set_password('SuperPass123!')
        db.session.add_all([regular_user, super_user])
        db.session.flush()

        db.session.add(UserRole(user_id=regular_user.id, role_id=staff_role.id))
        db.session.add(UserRole(user_id=super_user.id, role_id=super_role.id))
        db.session.commit()
        clinic_id = c.id

    # 1. Regular user is forbidden
    client.post('/auth/login', data={'email': 'regular@test.com', 'password': 'Pass123!'})
    assert client.get('/superadmin/clinics').status_code == 403
    client.post('/auth/logout')

    # 2. SuperAdmin has access
    client.post('/auth/login', data={'email': 'super@petcare360.com', 'password': 'SuperPass123!'})
    assert client.get('/superadmin/clinics').status_code == 200

    # 3. SuperAdmin suspends clinic
    res = client.post(f'/superadmin/clinics/{clinic_id}/toggle-status', data={'action': 'suspend'}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        target = db.session.get(Clinic, clinic_id)
        assert target.subscription_status == 'suspended'
        assert target.is_active is False
