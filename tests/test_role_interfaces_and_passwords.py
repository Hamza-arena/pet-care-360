import pytest
from app.extensions import db
from app.models import Clinic, Role, User, UserRole, Owner, Pet, Species


@pytest.fixture
def test_setup(app):
    with app.app_context():
        # Setup clinic
        clinic = Clinic.query.first()
        if not clinic:
            clinic = Clinic(name="Central Vet Clinic", currency="USD")
            db.session.add(clinic)
            db.session.commit()

        # Ensure roles exist
        for role_name in ['Admin', 'Doctor', 'Staff', 'Receptionist', 'User']:
            if not Role.query.filter(Role.name.ilike(role_name)).first():
                db.session.add(Role(name=role_name))
        db.session.commit()

        # Setup 4 distinct users with designated passwords
        admin = User.query.filter_by(email='admin@petcare360.com').first()
        if not admin:
            admin = User(email='admin@petcare360.com', username='admin_role_test', clinic_id=clinic.id)
            db.session.add(admin)
        admin.set_password('1790')
        admin_role = Role.query.filter(Role.name.ilike('Admin')).first()
        if not any(r.name.lower() == 'admin' for r in admin.roles):
            db.session.add(UserRole(user_id=admin.id, role_id=admin_role.id))

        doctor = User.query.filter_by(email='doctor@petcare360.com').first()
        if not doctor:
            doctor = User(email='doctor@petcare360.com', username='doctor_role_test', clinic_id=clinic.id)
            db.session.add(doctor)
        doctor.set_password('1567')
        doctor_role = Role.query.filter(Role.name.ilike('Doctor')).first()
        if not any(r.name.lower() == 'doctor' for r in doctor.roles):
            db.session.add(UserRole(user_id=doctor.id, role_id=doctor_role.id))

        staff = User.query.filter_by(email='staff@petcare360.com').first()
        if not staff:
            staff = User(email='staff@petcare360.com', username='staff_role_test', clinic_id=clinic.id)
            db.session.add(staff)
        staff.set_password('1234')
        staff_role = Role.query.filter(Role.name.ilike('Staff')).first()
        if not any(r.name.lower() == 'staff' for r in staff.roles):
            db.session.add(UserRole(user_id=staff.id, role_id=staff_role.id))

        db.session.commit()
    yield


def test_configured_passwords_login(client, test_setup):
    """Staff password is 1234, Doctor is 1567, Admin is 1790."""
    # Test Admin login with 1790
    resp_admin = client.post('/auth/login', data={'email': 'admin@petcare360.com', 'password': '1790'}, follow_redirects=True)
    assert resp_admin.status_code == 200
    assert b"Hospital Dashboard" in resp_admin.data or b"Clinical Operations Dashboard" in resp_admin.data
    client.post('/auth/logout')

    # Test Doctor login with 1567
    resp_doc = client.post('/auth/login', data={'email': 'doctor@petcare360.com', 'password': '1567'}, follow_redirects=True)
    assert resp_doc.status_code == 200
    assert b"Doctor Clinical Dashboard" in resp_doc.data or b"Doctor Cockpit" in resp_doc.data
    client.post('/auth/logout')

    # Test Staff login with 1234
    resp_staff = client.post('/auth/login', data={'email': 'staff@petcare360.com', 'password': '1234'}, follow_redirects=True)
    assert resp_staff.status_code == 200
    assert b"Front Desk" in resp_staff.data or b"Reception" in resp_staff.data
    client.post('/auth/logout')


def test_user_registration_and_password_saving(client, test_setup, app):
    """User registers and their password is saved directly from the web interface."""
    reg_data = {
        'first_name': 'Ali',
        'last_name': 'Raza',
        'email': 'ali_owner@example.com',
        'phone': '+923001234567',
        'password': 'AliPassword123!',
        'confirm_password': 'AliPassword123!',
        'pet_name': 'Milo',
        'pet_species': 'Cat'
    }
    resp = client.post('/auth/register', data=reg_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Pet Owner Portal" in resp.data
    assert b"Milo" in resp.data

    # Verify user was saved in DB and can authenticate with chosen password
    with app.app_context():
        user = User.query.filter_by(email='ali_owner@example.com').first()
        assert user is not None
        assert user.check_password('AliPassword123!')
        assert user.has_role('User')

    # Sign out and log back in using the interface-saved password
    client.post('/auth/logout')
    login_resp = client.post('/auth/login', data={'email': 'ali_owner@example.com', 'password': 'AliPassword123!'}, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Pet Owner Portal" in login_resp.data


def test_user_change_password_interface(client, test_setup):
    """User can change their password from the web interface."""
    # Login as staff first
    client.post('/auth/login', data={'email': 'staff@petcare360.com', 'password': '1234'})

    # Change password through interface
    change_resp = client.post('/auth/change-password', data={
        'current_password': '1234',
        'new_password': 'NewStaffPass999!',
        'confirm_new_password': 'NewStaffPass999!'
    }, follow_redirects=True)
    assert change_resp.status_code == 200
    assert b"updated and saved successfully" in change_resp.data

    # Verify old password fails
    client.post('/auth/logout')
    fail_resp = client.post('/auth/login', data={'email': 'staff@petcare360.com', 'password': '1234'})
    assert b"Invalid email or password" in fail_resp.data

    # Verify new password succeeds
    success_resp = client.post('/auth/login', data={'email': 'staff@petcare360.com', 'password': 'NewStaffPass999!'}, follow_redirects=True)
    assert success_resp.status_code == 200
    assert b"Front Desk" in success_resp.data

    # Revert back to 1234 for consistency
    client.post('/auth/change-password', data={
        'current_password': 'NewStaffPass999!',
        'new_password': '1234',
        'confirm_new_password': '1234'
    })

