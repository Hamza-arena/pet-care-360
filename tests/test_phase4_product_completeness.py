import io
from datetime import date, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.appointments import Appointment, AppointmentType
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.finance import Invoice, InvoiceItem
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.models.pharmacy import Medicine


def test_migrations_phase4_upgrade_and_downgrade(tmp_path):
    """Verify that Alembic can cleanly upgrade to Phase 4 (photo_filename) and downgrade back."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app import create_app
    from app.config import TestingConfig

    test_db = tmp_path / "test_p4_migration.db"
    db_uri = f"sqlite:///{test_db}"

    class BlankMigrationConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = db_uri

    blank_app = create_app(BlankMigrationConfig)
    with blank_app.app_context():
        alembic_cfg = AlembicConfig("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")

        # Upgrade to head
        command.upgrade(alembic_cfg, 'head')
        # Downgrade to Phase 3
        command.downgrade(alembic_cfg, '5e1b2c3d4f5a')
        # Re-upgrade to head
        command.upgrade(alembic_cfg, 'head')


def test_edit_owner_workflow(client, app):
    """Verify editing owner details updates record and redirects properly."""
    with app.app_context():
        clinic = Clinic(name="Owner Clinic", currency="PKR")
        role = Role(name="Receptionist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="rec_owner", email="rec_owner@test.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        owner = Owner(
            first_name="Original",
            last_name="Name",
            email="original@test.com",
            phone="03001234567",
            clinic_id=clinic.id,
        )
        db.session.add(owner)
        db.session.commit()
        owner_id = owner.id

    client.post('/auth/login', data={'email': 'rec_owner@test.com', 'password': 'Pass123!'})

    # GET edit form
    res = client.get(f'/owners/{owner_id}/edit')
    assert res.status_code == 200

    # POST updated details
    res = client.post(f'/owners/{owner_id}/edit', data={
        'first_name': 'Updated',
        'last_name': 'Customer',
        'email': 'updated@test.com',
        'phone': '03009876543',
        'notes': 'Preferred client',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated_owner = db.session.get(Owner, owner_id)
        assert updated_owner.first_name == 'Updated'
        assert updated_owner.last_name == 'Customer'
        assert updated_owner.phone == '03009876543'


def test_edit_medicine_workflow(client, app):
    """Verify editing a medicine in pharmacy updates price and threshold."""
    with app.app_context():
        clinic = Clinic(name="Med Clinic", currency="PKR")
        role = Role(name="Pharmacist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="pharm_edit", email="pharm_edit@test.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        med = Medicine(
            name="Augmentin",
            category="Antibiotic",
            unit="Tablet",
            base_price=Decimal("20.00"),
            minimum_stock=10,
            clinic_id=clinic.id,
        )
        db.session.add(med)
        db.session.commit()
        med_id = med.id

    client.post('/auth/login', data={'email': 'pharm_edit@test.com', 'password': 'Pass123!'})

    res = client.get(f'/pharmacy/{med_id}/edit')
    assert res.status_code == 200

    res = client.post(f'/pharmacy/{med_id}/edit', data={
        'name': 'Augmentin 625mg',
        'category': 'Antibiotic',
        'unit': 'Tablet',
        'base_price': 25.50,
        'minimum_stock': 15,
        'requires_prescription': True,
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated_med = db.session.get(Medicine, med_id)
        assert updated_med.name == 'Augmentin 625mg'
        assert updated_med.base_price == Decimal('25.50')
        assert updated_med.minimum_stock == 15


def test_appointment_reschedule_and_cancel(client, app):
    """Verify appointment rescheduling with conflict checks and quick cancellation."""
    with app.app_context():
        clinic = Clinic(name="Apt Clinic", currency="PKR")
        role = Role(name="Receptionist")
        doc_role = Role(name="Doctor")
        db.session.add_all([clinic, role, doc_role])
        db.session.flush()

        staff = User(username="rec_apt", email="rec_apt@test.com", clinic_id=clinic.id, is_active=True)
        staff.set_password("Pass123!")
        doc = User(username="dr_apt", email="dr_apt@test.com", clinic_id=clinic.id, is_active=True)
        doc.set_password("Pass123!")
        db.session.add_all([staff, doc])
        db.session.flush()

        db.session.add(UserRole(user_id=staff.id, role_id=role.id))
        db.session.add(UserRole(user_id=doc.id, role_id=doc_role.id))

        species = Species(name="Feline")
        db.session.add(species)
        db.session.flush()

        owner = Owner(first_name="Jane", last_name="Doe", email="jane@doe.com", phone="03001122334", clinic_id=clinic.id)
        db.session.add(owner)
        db.session.flush()

        pet = Pet(name="Milo", species_id=species.id, owner_id=owner.id)
        apt_type = AppointmentType(name="Checkup", duration_minutes=30, base_fee=Decimal("40.00"))
        db.session.add_all([pet, apt_type])
        db.session.commit()

        apt = Appointment(
            pet_id=pet.id,
            doctor_id=doc.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type.id,
            appointment_date=date.today() + timedelta(days=5),
            appointment_time=time(11, 0),
            status='Scheduled',
        )
        db.session.add(apt)
        db.session.commit()
        apt_id = apt.id
        doc_id = doc.id
        pet_id = pet.id
        type_id = apt_type.id
        clinic_id = clinic.id

    client.post('/auth/login', data={'email': 'rec_apt@test.com', 'password': 'Pass123!'})

    # Reschedule to 14:00 (no conflict)
    new_date = (date.today() + timedelta(days=6)).strftime('%Y-%m-%d')
    res = client.post(f'/appointments/{apt_id}/edit', data={
        'pet_id': pet_id,
        'doctor_id': doc_id,
        'clinic_id': clinic_id,
        'appointment_type_id': type_id,
        'appointment_date': new_date,
        'appointment_time': '14:00',
        'reason': 'Rescheduled by owner',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated_apt = db.session.get(Appointment, apt_id)
        assert updated_apt.appointment_time == time(14, 0)

    # Cancel appointment
    res = client.post(f'/appointments/{apt_id}/cancel', data={'notes': 'Cancelled by phone'}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        cancelled_apt = db.session.get(Appointment, apt_id)
        assert cancelled_apt.status == 'Cancelled'


def test_invoice_printable_view(client, app):
    """Verify printable invoice page returns 200 and contains invoice elements."""
    with app.app_context():
        clinic = Clinic(name="Print Clinic", currency="PKR")
        role = Role(name="Receptionist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="rec_print", email="rec_print@test.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        owner = Owner(first_name="Bill", last_name="Gates", email="bill@gates.com", phone="03005556677", clinic_id=clinic.id)
        db.session.add(owner)
        db.session.flush()

        inv = Invoice(
            clinic_id=clinic.id,
            invoice_number="INV-2026-PRINT",
            owner_id=owner.id,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("16.00"),
            total_amount=Decimal("116.00"),
            paid_amount=Decimal("116.00"),
            status='Paid',
        )
        db.session.add(inv)
        db.session.flush()

        item = InvoiceItem(invoice_id=inv.id, description="Exam", quantity=1, unit_price=Decimal("100.00"), total_price=Decimal("100.00"))
        db.session.add(item)
        db.session.commit()
        inv_id = inv.id

    client.post('/auth/login', data={'email': 'rec_print@test.com', 'password': 'Pass123!'})

    res = client.get(f'/billing/invoices/{inv_id}/print')
    assert res.status_code == 200
    assert b"INV-2026-PRINT" in res.data
    assert b"Print Clinic" in res.data


def test_csv_reports_export(client, app):
    """Verify financial, inventory, and appointment CSV exports return 200 with text/csv."""
    with app.app_context():
        clinic = Clinic(name="Report Clinic", currency="PKR")
        role = Role(name="Admin")
        db.session.add_all([clinic, role])
        db.session.flush()

        admin = User(username="rep_admin", email="rep_admin@test.com", clinic_id=clinic.id, is_active=True)
        admin.set_password("Pass123!")
        db.session.add(admin)
        db.session.flush()
        db.session.add(UserRole(user_id=admin.id, role_id=role.id))

        owner = Owner(first_name="Report", last_name="User", email="rep@test.com", phone="03007778899", clinic_id=clinic.id)
        db.session.add(owner)
        db.session.flush()

        inv = Invoice(clinic_id=clinic.id, invoice_number="INV-REP-01", owner_id=owner.id, total_amount=Decimal("50.00"), status='Paid')
        med = Medicine(clinic_id=clinic.id, name="TestMed", base_price=Decimal("10.00"), minimum_stock=5)
        db.session.add_all([inv, med])
        db.session.commit()

    client.post('/auth/login', data={'email': 'rep_admin@test.com', 'password': 'Pass123!'})

    # Billing CSV
    res_bill = client.get('/billing/export/csv')
    assert res_bill.status_code == 200
    assert 'text/csv' in res_bill.headers.get('Content-Type', '')
    assert b"INV-REP-01" in res_bill.data

    # Pharmacy CSV
    res_pharm = client.get('/pharmacy/export/csv')
    assert res_pharm.status_code == 200
    assert 'text/csv' in res_pharm.headers.get('Content-Type', '')
    assert b"TestMed" in res_pharm.data

    # Appointments CSV
    res_apt = client.get('/appointments/export/csv')
    assert res_apt.status_code == 200
    assert 'text/csv' in res_apt.headers.get('Content-Type', '')


def test_fast_search(client, app):
    """Verify /search endpoint returns matched owners and pets."""
    with app.app_context():
        clinic = Clinic(name="Search Clinic", currency="PKR")
        role = Role(name="Receptionist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="search_user", email="search@test.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        species = Species(name="Canine")
        db.session.add(species)
        db.session.flush()

        owner = Owner(first_name="Alexander", last_name="Hamilton", email="alex@hamilton.com", phone="03004443322", clinic_id=clinic.id)
        db.session.add(owner)
        db.session.flush()

        pet = Pet(name="Sherlock", microchip_number="CHIP-998877", species_id=species.id, owner_id=owner.id)
        db.session.add(pet)
        db.session.commit()

    client.post('/auth/login', data={'email': 'search@test.com', 'password': 'Pass123!'})

    # Search by owner name
    res1 = client.get('/search?q=Hamilton')
    assert res1.status_code == 200
    assert b"Hamilton" in res1.data

    # Search by microchip
    res2 = client.get('/search?q=CHIP-998877')
    assert res2.status_code == 200
    assert b"Sherlock" in res2.data


def test_secure_pet_photo_upload(client, app):
    """Verify valid image upload succeeds, while executable (.exe/.php) and oversized files (>2MB) are rejected."""
    with app.app_context():
        clinic = Clinic(name="Upload Clinic", currency="PKR")
        role = Role(name="Receptionist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="upload_user", email="upload@test.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        species = Species(name="Avian")
        db.session.add(species)
        db.session.flush()

        owner = Owner(first_name="Upload", last_name="Owner", email="up@owner.com", phone="03001239999", clinic_id=clinic.id)
        db.session.add(owner)
        db.session.flush()

        pet = Pet(name="Parrot", species_id=species.id, owner_id=owner.id)
        db.session.add(pet)
        db.session.commit()
        pet_id = pet.id

    client.post('/auth/login', data={'email': 'upload@test.com', 'password': 'Pass123!'})

    # 1. Valid PNG upload
    valid_png = (io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummyimagecontent"), 'pet.png')
    res_valid = client.post(f'/pets/{pet_id}/photo', data={'photo': valid_png}, content_type='multipart/form-data', follow_redirects=True)
    assert res_valid.status_code == 200

    with app.app_context():
        updated_pet = db.session.get(Pet, pet_id)
        assert updated_pet.photo_filename is not None
        assert updated_pet.photo_filename.endswith('.png')

    # 2. Malicious executable (.exe) upload -> must return 400
    bad_exe = (io.BytesIO(b"MZdummyexecutablecontent"), 'virus.exe')
    res_exe = client.post(f'/pets/{pet_id}/photo', data={'photo': bad_exe}, content_type='multipart/form-data')
    assert res_exe.status_code == 400

    # 3. Malicious script (.php) upload -> must return 400
    bad_php = (io.BytesIO(b"<?php echo 'hack'; ?>"), 'exploit.php')
    res_php = client.post(f'/pets/{pet_id}/photo', data={'photo': bad_php}, content_type='multipart/form-data')
    assert res_php.status_code == 400

    # 4. Oversized file (>2MB) upload -> must return 400
    huge_file = (io.BytesIO(b"A" * (2 * 1024 * 1024 + 100)), 'huge.jpg')
    res_huge = client.post(f'/pets/{pet_id}/photo', data={'photo': huge_file}, content_type='multipart/form-data')
    assert res_huge.status_code == 400
