from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import event

from app.extensions import db
from app.models.appointments import Appointment, AppointmentType
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.finance import Invoice, PaymentMethod
from app.models.laboratory import LabOrder, LabTest
from app.models.medical import MedicalRecord
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.models.pharmacy import Medicine, MedicineBatch


def test_healthz_endpoint_healthy(client):
    """Verify /healthz returns 200 and healthy status when database is operational."""
    res = client.get('/healthz')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'healthy'
    assert data['database'] == 'connected'
    assert 'timestamp' in data


def test_healthz_endpoint_unhealthy(client):
    """Verify /healthz returns 503 and error message when database connection fails."""
    with patch('app.extensions.db.session.execute', side_effect=Exception('DB Connection Refused')):
        res = client.get('/healthz')
        assert res.status_code == 503
        data = res.get_json()
        assert data['status'] == 'unhealthy'
        assert data['database'] == 'error'
        assert 'DB Connection Refused' in data['error']


def test_custom_error_handlers(client):
    """Verify 404 page handler renders custom template without crashing."""
    res = client.get('/this-path-definitely-does-not-exist-404')
    assert res.status_code == 404
    assert b'404' in res.data or b'Page Not Found' in res.data


def test_dashboard_query_efficiency_and_n_plus_one_elimination(client, app):
    """Verify that dashboard renders with a fixed, low query count and does not suffer from N+1 query loops."""
    with app.app_context():
        clinic = Clinic(name='Bench Clinic', currency='PKR')
        role = Role(name='Receptionist')
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username='bench_user', email='bench@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        species = Species(name='BenchSpecies')
        db.session.add(species)
        db.session.flush()

        # Seed 10 owners and pets
        for i in range(10):
            owner = Owner(
                clinic_id=clinic.id,
                first_name=f'Owner{i}',
                last_name='Test',
                phone=f'030000000{i:02d}',
                email=f'bench_owner{i}@test.com',
            )
            db.session.add(owner)
            db.session.flush()

            pet = Pet(owner_id=owner.id, species_id=species.id, name=f'Pet{i}')
            db.session.add(pet)

        # Seed 10 medicines with multiple batches
        for i in range(10):
            med = Medicine(
                clinic_id=clinic.id,
                name=f'Medicine-{i}',
                unit='Tablet',
                minimum_stock=15,
                base_price=Decimal('20.00'),
            )
            db.session.add(med)
            db.session.flush()

            for b in range(2):
                batch = MedicineBatch(
                    medicine_id=med.id,
                    batch_number=f'B-{i}-{b}',
                    quantity_received=10,
                    quantity_remaining=5,
                    expiry_date=date.today() + timedelta(days=60),
                    purchase_price=Decimal('10.00'),
                    selling_price=Decimal('20.00'),
                )
                db.session.add(batch)

        db.session.commit()

    # Login
    client.post('/auth/login', data={'email': 'bench@test.com', 'password': 'Pass123!'})

    # Track SQL queries executed during dashboard render
    queries_executed = []

    def query_listener(conn, cursor, statement, parameters, context, executemany):
        queries_executed.append(statement)

    with app.app_context():
        engine = db.engine

    event.listen(engine, 'before_cursor_execute', query_listener)

    try:
        res = client.get('/')
        assert res.status_code == 200
        # With single aggregate subquery and eager loads, query count is tightly bounded <= 15 queries total.
        assert len(queries_executed) <= 15, f"Expected <= 15 queries, got {len(queries_executed)}"
    finally:
        event.remove(engine, 'before_cursor_execute', query_listener)


def test_billing_create_item_and_payment_flow(client, app):
    """Verify complete billing lifecycle: create invoice, add line item, record payment, verify balance."""
    with app.app_context():
        clinic = Clinic(name='Fin Clinic', currency='PKR')
        role = Role(name='Receptionist')
        pm = PaymentMethod(name='Cash', is_active=True)
        db.session.add_all([clinic, role, pm])
        db.session.flush()

        user = User(username='fin_user', email='fin@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        owner = Owner(
            clinic_id=clinic.id,
            first_name='Saleem',
            last_name='Akhtar',
            phone='03007654321',
            email='saleem@fin.com',
        )
        db.session.add(owner)
        db.session.commit()
        owner_id = owner.id
        pm_id = pm.id

    client.post('/auth/login', data={'email': 'fin@test.com', 'password': 'Pass123!'})

    # View billing index
    res = client.get('/billing/')
    assert res.status_code == 200

    # Create invoice
    res = client.post('/billing/invoices/new', data={
        'owner_id': owner_id,
        'pet_id': 0,
        'discount_amount': '0.00',
        'tax_amount': '0.00',
        'notes': 'Dental checkup',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        inv = Invoice.query.filter_by(owner_id=owner_id).first()
        assert inv is not None
        inv_id = inv.id

    # Add item
    res = client.post(f'/billing/invoices/{inv_id}/items/add', data={
        'description': 'Dental Cleaning',
        'item_type': 'Consultation',
        'quantity': 1,
        'unit_price': 1500.00,
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        inv = db.session.get(Invoice, inv_id)
        # Clinic tax rate is 16%, so 1500 + 16% tax (240) = 1740.00
        assert inv.subtotal == Decimal('1500.00')
        assert inv.total_amount == Decimal('1740.00')
        assert inv.balance_due == Decimal('1740.00')

    # Record payment
    res = client.post(f'/billing/invoices/{inv_id}/payments/new', data={
        'payment_method_id': pm_id,
        'amount': 1740.00,
        'transaction_reference': 'CASH-001',
        'notes': 'Paid in full',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        inv = db.session.get(Invoice, inv_id)
        assert inv.paid_amount == Decimal('1740.00')
        assert inv.balance_due == Decimal('0.00')
        assert inv.status == 'Paid'


def test_routes_coverage_expansion(client, app):
    """Exercise owners, pets, appointments, medical, lab, and admin routes to ensure broad test coverage."""
    with app.app_context():
        clinic = Clinic(name='Ops Clinic', currency='PKR')
        admin_role = Role(name='Admin')
        doc_role = Role(name='Doctor')
        db.session.add_all([clinic, admin_role, doc_role])
        db.session.flush()

        admin = User(username='admin_ops', email='admin_ops@test.com', clinic_id=clinic.id, is_active=True)
        admin.set_password('AdminPass123!')
        db.session.add(admin)
        db.session.flush()
        db.session.add(UserRole(user_id=admin.id, role_id=admin_role.id))
        db.session.add(UserRole(user_id=admin.id, role_id=doc_role.id))

        species = Species(name='Canine-Ops')
        db.session.add(species)
        db.session.flush()

        owner = Owner(
            clinic_id=clinic.id,
            first_name='Bilal',
            last_name='Saeed',
            phone='03001112233',
            email='bilal@ops.com',
        )
        db.session.add(owner)
        db.session.flush()

        pet = Pet(owner_id=owner.id, species_id=species.id, name='Rocky')
        db.session.add(pet)
        db.session.flush()

        apt_type = AppointmentType(name='General Check', duration_minutes=30, base_fee=Decimal('500.00'))
        db.session.add(apt_type)
        db.session.flush()

        apt = Appointment(
            clinic_id=clinic.id,
            pet_id=pet.id,
            doctor_id=admin.id,
            appointment_type_id=apt_type.id,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            status='Scheduled',
        )
        db.session.add(apt)
        db.session.flush()

        med_rec = MedicalRecord(
            clinic_id=clinic.id,
            pet_id=pet.id,
            doctor_id=admin.id,
            visit_date=datetime.now(UTC),
            chief_complaint='Lethargy',
            examination_notes='Mild dehydration',
        )
        db.session.add(med_rec)
        db.session.flush()

        lab_test = LabTest(name='Complete Blood Count', code='CBC', base_price=Decimal('800.00'))
        db.session.add(lab_test)
        db.session.flush()

        lab_order = LabOrder(
            clinic_id=clinic.id,
            pet_id=pet.id,
            doctor_id=admin.id,
            status='Pending',
            priority='Routine',
        )
        db.session.add(lab_order)
        db.session.commit()

        owner_id = owner.id
        pet_id = pet.id
        apt_id = apt.id
        med_rec_id = med_rec.id

    client.post('/auth/login', data={'email': 'admin_ops@test.com', 'password': 'AdminPass123!'})

    # Owners and pets list & details
    assert client.get('/owners/').status_code == 200
    assert client.get(f'/owners/{owner_id}').status_code == 200
    assert client.get('/pets/').status_code == 200
    assert client.get(f'/pets/{pet_id}').status_code == 200

    # Appointments list & details
    assert client.get('/appointments/').status_code == 200
    assert client.get(f'/appointments/{apt_id}').status_code == 200

    # Medical records list & details
    assert client.get('/medical/').status_code == 200
    assert client.get(f'/medical/{med_rec_id}').status_code == 200

    # Laboratory list
    assert client.get('/lab/').status_code == 200

    # Admin management views
    assert client.get('/admin/staff').status_code == 200
    assert client.get('/admin/clinics').status_code == 200
    assert client.get('/admin/audit-logs').status_code == 200
    assert client.get('/admin/recycle-bin').status_code == 200


def test_additional_coverage_for_clinical_workflows(client, app):
    """Exercise owner creation and vaccination tabs to exceed 80% coverage target."""
    with app.app_context():
        clinic = Clinic(name='Clinical Coverage Clinic', currency='PKR')
        admin_role = Role(name='Admin')
        doc_role = Role(name='Doctor')
        db.session.add_all([clinic, admin_role, doc_role])
        db.session.flush()

        user = User(username='clin_user', email='clin@test.com', clinic_id=clinic.id, is_active=True)
        user.set_password('Pass123!')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.session.add(UserRole(user_id=user.id, role_id=doc_role.id))
        db.session.commit()

    client.post('/auth/login', data={'email': 'clin@test.com', 'password': 'Pass123!'})

    # Vaccination views
    assert client.get('/vaccination/?tab=vaccines').status_code == 200
    assert client.get('/vaccination/?tab=deworming').status_code == 200
    assert client.get('/vaccination/?tab=reminders').status_code == 200

    # Create Owner form view and submit
    res = client.get('/owners/new')
    assert res.status_code == 200

    res = client.post('/owners/new', data={
        'first_name': 'Hamza',
        'last_name': 'Ali',
        'email': 'hamza@test.com',
        'phone': '03001239876',
        'street_address': 'Street 10',
        'city': 'Lahore',
    }, follow_redirects=True)
    assert res.status_code == 200
