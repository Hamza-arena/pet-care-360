from datetime import date, time

from app.extensions import db
from app.models.appointments import Appointment, AppointmentType
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.finance import Invoice
from app.models.medical import MedicalRecord
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.models.pharmacy import Medicine


def setup_multi_tenant_scenario(app):
    """Set up two distinct clinics with independent doctors, owners, and patients."""
    with app.app_context():
        # Clinics
        clinic_a = Clinic(name='Clinic Alpha', city='Alpha City', is_active=True)
        clinic_b = Clinic(name='Clinic Beta', city='Beta City', is_active=True)
        db.session.add_all([clinic_a, clinic_b])
        db.session.flush()

        # Roles
        doctor_role = Role.query.filter_by(name='Doctor').first()
        if not doctor_role:
            doctor_role = Role(name='Doctor', description='Veterinarian')
            db.session.add(doctor_role)
            db.session.flush()

        # Doctor for Clinic A
        doc_a = User(
            email='dr_alpha@clinic.com',
            username='dr_alpha',
            first_name='Alpha',
            last_name='Doctor',
            clinic_id=clinic_a.id,
            is_active=True
        )
        doc_a.set_password('Doctor@123')

        # Doctor for Clinic B
        doc_b = User(
            email='dr_beta@clinic.com',
            username='dr_beta',
            first_name='Beta',
            last_name='Doctor',
            clinic_id=clinic_b.id,
            is_active=True
        )
        doc_b.set_password('Doctor@123')

        db.session.add_all([doc_a, doc_b])
        db.session.flush()

        db.session.add_all([
            UserRole(user_id=doc_a.id, role_id=doctor_role.id),
            UserRole(user_id=doc_b.id, role_id=doctor_role.id)
        ])

        # Species
        dog_spec = Species.query.filter_by(name='Canine').first()
        if not dog_spec:
            dog_spec = Species(name='Canine')
            db.session.add(dog_spec)
            db.session.flush()

        # Owners
        owner_a = Owner(
            clinic_id=clinic_a.id,
            first_name='Alice',
            last_name='AlphaClient',
            email='alice@alpha.com',
            phone='111222333'
        )
        owner_b = Owner(
            clinic_id=clinic_b.id,
            first_name='Bob',
            last_name='BetaClient',
            email='bob@beta.com',
            phone='444555666'
        )
        db.session.add_all([owner_a, owner_b])
        db.session.flush()

        # Pets
        pet_a = Pet(owner_id=owner_a.id, species_id=dog_spec.id, name='Rex Alpha', gender='Male')
        pet_b = Pet(owner_id=owner_b.id, species_id=dog_spec.id, name='Buddy Beta', gender='Male')
        db.session.add_all([pet_a, pet_b])
        db.session.flush()

        # Appointment Type
        apt_type = AppointmentType.query.first()
        if not apt_type:
            apt_type = AppointmentType(name='Checkup', duration_minutes=30, base_fee=50.0)
            db.session.add(apt_type)
            db.session.flush()

        # Appointments
        apt_a = Appointment(
            clinic_id=clinic_a.id,
            pet_id=pet_a.id,
            doctor_id=doc_a.id,
            appointment_type_id=apt_type.id,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            status='Scheduled'
        )
        apt_b = Appointment(
            clinic_id=clinic_b.id,
            pet_id=pet_b.id,
            doctor_id=doc_b.id,
            appointment_type_id=apt_type.id,
            appointment_date=date.today(),
            appointment_time=time(11, 0),
            status='Scheduled'
        )
        db.session.add_all([apt_a, apt_b])
        db.session.flush()

        # Invoices
        inv_a = Invoice(
            clinic_id=clinic_a.id,
            invoice_number='INV-ALPHA-001',
            owner_id=owner_a.id,
            pet_id=pet_a.id,
            total_amount=100.0,
            status='Unpaid'
        )
        inv_b = Invoice(
            clinic_id=clinic_b.id,
            invoice_number='INV-BETA-001',
            owner_id=owner_b.id,
            pet_id=pet_b.id,
            total_amount=200.0,
            status='Unpaid'
        )
        db.session.add_all([inv_a, inv_b])
        db.session.flush()

        # Medicines
        med_a = Medicine(clinic_id=clinic_a.id, name='Amoxicillin Alpha', category='Antibiotic')
        med_b = Medicine(clinic_id=clinic_b.id, name='Ciprofloxacin Beta', category='Antibiotic')
        db.session.add_all([med_a, med_b])
        db.session.flush()

        # Medical Records
        rec_a = MedicalRecord(
            clinic_id=clinic_a.id,
            pet_id=pet_a.id,
            doctor_id=doc_a.id,
            chief_complaint='Alpha Checkup'
        )
        rec_b = MedicalRecord(
            clinic_id=clinic_b.id,
            pet_id=pet_b.id,
            doctor_id=doc_b.id,
            chief_complaint='Beta Checkup'
        )
        db.session.add_all([rec_a, rec_b])
        db.session.commit()

        return {
            'clinic_a_id': clinic_a.id,
            'clinic_b_id': clinic_b.id,
            'doc_a_id': doc_a.id,
            'doc_b_id': doc_b.id,
            'owner_a_id': owner_a.id,
            'owner_b_id': owner_b.id,
            'pet_a_id': pet_a.id,
            'pet_b_id': pet_b.id,
            'apt_a_id': apt_a.id,
            'apt_b_id': apt_b.id,
            'inv_a_id': inv_a.id,
            'inv_b_id': inv_b.id,
            'med_a_id': med_a.id,
            'med_b_id': med_b.id,
            'rec_a_id': rec_a.id,
            'rec_b_id': rec_b.id
        }


def make_client_for_user(app, user_id):
    """Create an authenticated test client for a specific user ID."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
    return client


def test_tenant_owners_list_isolation(app):
    """Clinic A doctor should see only Clinic A owners, never Clinic B."""
    ids = setup_multi_tenant_scenario(app)

    # Clinic A Doctor
    client_a = make_client_for_user(app, ids['doc_a_id'])
    resp_a = client_a.get('/owners/')
    assert resp_a.status_code == 200
    assert 'Alice' in resp_a.get_data(as_text=True)
    assert 'Bob' not in resp_a.get_data(as_text=True)

    # Clinic B Doctor
    client_b = make_client_for_user(app, ids['doc_b_id'])
    resp_b = client_b.get('/owners/')
    assert resp_b.status_code == 200
    assert 'Bob' in resp_b.get_data(as_text=True)
    assert 'Alice' not in resp_b.get_data(as_text=True)


def test_tenant_owner_direct_access_denied(app):
    """Clinic A doctor cannot view Clinic B's owner profile via direct URL."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    client_b = make_client_for_user(app, ids['doc_b_id'])

    # Doctor A trying to access Owner B
    assert client_a.get(f"/owners/{ids['owner_b_id']}").status_code == 404

    # Doctor B trying to access Owner A
    assert client_b.get(f"/owners/{ids['owner_a_id']}").status_code == 404


def test_tenant_pet_direct_access_denied(app):
    """Clinic A doctor cannot access Clinic B's pet dossier."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    client_b = make_client_for_user(app, ids['doc_b_id'])

    assert client_a.get(f"/pets/{ids['pet_b_id']}").status_code == 404
    assert client_b.get(f"/pets/{ids['pet_a_id']}").status_code == 404


def test_tenant_appointment_access_denied(app):
    """Clinic A doctor cannot view or delete Clinic B appointments."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    # Direct view blocked
    assert client_a.get(f"/appointments/{ids['apt_b_id']}").status_code == 404
    # Deletion blocked
    assert client_a.post(f"/appointments/{ids['apt_b_id']}/delete").status_code == 404


def test_tenant_invoice_access_denied(app):
    """Clinic A user cannot view or delete Clinic B invoices."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    assert client_a.get(f"/billing/invoices/{ids['inv_b_id']}").status_code == 404
    assert client_a.post(f"/billing/invoices/{ids['inv_b_id']}/delete").status_code == 404


def test_tenant_medical_record_access_denied(app):
    """Clinic A doctor cannot view or delete Clinic B medical records."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    assert client_a.get(f"/medical/{ids['rec_b_id']}").status_code == 404
    assert client_a.post(f"/medical/{ids['rec_b_id']}/delete").status_code == 404


def test_tenant_pharmacy_medicine_isolation(app):
    """Clinic A staff only see Clinic A medicines in their inventory list."""
    ids = setup_multi_tenant_scenario(app)

    client_a = make_client_for_user(app, ids['doc_a_id'])
    resp = client_a.get('/pharmacy/')
    assert resp.status_code == 200
    assert 'Amoxicillin Alpha' in resp.get_data(as_text=True)
    assert 'Ciprofloxacin Beta' not in resp.get_data(as_text=True)

    # Direct view blocked
    assert client_a.get(f"/pharmacy/{ids['med_b_id']}").status_code == 404


def test_superadmin_global_cross_tenant_visibility(auth_client, app):
    """SuperAdmin with no specific clinic filter has global visibility across all clinics."""
    ids = setup_multi_tenant_scenario(app)

    # auth_client is Admin without clinic_id
    resp = auth_client.get('/owners/')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'Alice' in data
    assert 'Bob' in data

    # Can access both clinics' records
    assert auth_client.get(f"/owners/{ids['owner_a_id']}").status_code == 200
    assert auth_client.get(f"/owners/{ids['owner_b_id']}").status_code == 200
