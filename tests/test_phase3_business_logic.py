from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.appointments import Appointment, AppointmentType
from app.models.auth import Role, User, UserRole
from app.models.clinic import Clinic
from app.models.finance import Invoice, InvoiceItem
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.models.pharmacy import Medicine, MedicineBatch
from app.utils.appointments import check_appointment_conflict
from app.utils.finance import (
    generate_next_invoice_number,
    recalculate_invoice,
    to_decimal,
)


def test_migrations_phase3_upgrade_and_downgrade(tmp_path):
    """Verify that Alembic can cleanly upgrade to Phase 3 and downgrade back."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app import create_app
    from app.config import TestingConfig

    test_db = tmp_path / "test_p3_migration.db"
    db_uri = f"sqlite:///{test_db}"

    class BlankMigrationConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = db_uri

    blank_app = create_app(BlankMigrationConfig)
    with blank_app.app_context():
        alembic_cfg = AlembicConfig("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")

        # Upgrade to Phase 3 revision
        command.upgrade(alembic_cfg, '5e1b2c3d4f5a')
        # Downgrade to Phase 2 revision
        command.downgrade(alembic_cfg, '0de89771a5af')
        # Re-upgrade to Phase 3
        command.upgrade(alembic_cfg, '5e1b2c3d4f5a')


def test_decimal_penny_accuracy(app):
    """Verify float inaccuracy 0.1 + 0.2 is strictly solved via Decimal (0.10 + 0.20 == 0.30)."""
    with app.app_context():
        # Setup clinic and owner
        clinic = Clinic(name="Decimal Test Clinic", currency="PKR", tax_rate=Decimal("10.00"))
        db.session.add(clinic)
        db.session.flush()

        owner = Owner(
            first_name="Penny",
            last_name="Tester",
            email="penny@test.com",
            phone="03001112233",
            clinic_id=clinic.id,
        )
        db.session.add(owner)
        db.session.flush()

        inv = Invoice(
            clinic_id=clinic.id,
            invoice_number="INV-TEST-0001",
            owner_id=owner.id,
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
        )
        db.session.add(inv)
        db.session.flush()

        # Add two items with prices 0.10 and 0.20
        item1 = InvoiceItem(
            invoice_id=inv.id,
            description="Item 1",
            quantity=1,
            unit_price=to_decimal("0.10"),
            total_price=to_decimal("0.10"),
        )
        item2 = InvoiceItem(
            invoice_id=inv.id,
            description="Item 2",
            quantity=1,
            unit_price=to_decimal("0.20"),
            total_price=to_decimal("0.20"),
        )
        db.session.add_all([item1, item2])
        db.session.flush()

        # In pure float, 0.1 + 0.2 != 0.3 (0.30000000000000004)
        assert (0.1 + 0.2) != 0.3

        # In our decimal recalculation, subtotal is EXACTLY 0.30
        recalculate_invoice(inv)
        assert inv.subtotal == Decimal("0.30")
        # 10% tax on 0.30 is 0.03 -> Total is 0.33
        assert inv.tax_amount == Decimal("0.03")
        assert inv.total_amount == Decimal("0.33")


def test_race_safe_sequential_invoice_numbering(tmp_path):
    """Concurrency test: 10 concurrent invoice generation requests must not produce duplicates."""
    from app import create_app
    from app.config import TestingConfig

    test_db = tmp_path / "concur_test.db"
    db_uri = f"sqlite:///{test_db}?timeout=30"

    class ConcurConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = db_uri

    concur_app = create_app(ConcurConfig)
    with concur_app.app_context():
        db.create_all()
        clinic = Clinic(name="Concur Clinic", currency="PKR", invoice_sequence=0)
        db.session.add(clinic)
        db.session.commit()
        clinic_id = clinic.id

    def generate_number(idx):
        with concur_app.app_context():
            num = generate_next_invoice_number(clinic_id)
            db.session.commit()
            return num

    with ThreadPoolExecutor(max_workers=4) as executor:
        numbers = list(executor.map(generate_number, range(10)))

    # All 10 must be unique
    assert len(numbers) == 10
    assert len(set(numbers)) == 10
    # Must be sequential
    year = datetime.now(UTC).strftime('%Y')
    for seq in range(1, 11):
        expected = f"INV-{year}-{seq:04d}"
        assert expected in numbers


def test_pharmacy_dispense_expired_batch_rejected(client, app):
    """Dispensing from an expired medicine batch must return HTTP 400."""
    with app.app_context():
        clinic = Clinic(name="Pharm Clinic", currency="PKR")
        staff_role = Role(name="Pharmacist")
        db.session.add_all([clinic, staff_role])
        db.session.flush()

        pharmacist = User(
            username="pharm1",
            email="pharm1@clinic.com",
            clinic_id=clinic.id,
            is_active=True,
        )
        pharmacist.set_password("Pass123!")
        db.session.add(pharmacist)
        db.session.flush()
        db.session.add(UserRole(user_id=pharmacist.id, role_id=staff_role.id))

        med = Medicine(name="Amoxicillin", clinic_id=clinic.id, base_price=Decimal("15.00"))
        db.session.add(med)
        db.session.flush()

        # Create expired batch (expired yesterday)
        expired_batch = MedicineBatch(
            medicine_id=med.id,
            batch_number="EXP-LOT-01",
            quantity_received=50,
            quantity_remaining=50,
            expiry_date=date.today() - timedelta(days=1),
        )
        db.session.add(expired_batch)
        db.session.commit()
        med_id = med.id
        batch_id = expired_batch.id

    # Login as pharmacist
    client.post('/auth/login', data={'email': 'pharm1@clinic.com', 'password': 'Pass123!'})

    # Try dispensing from expired batch -> must return 400
    res = client.post(f'/pharmacy/{med_id}/dispense', data={
        'batch_id': batch_id,
        'quantity': 5,
        'notes': 'Should fail',
    })
    assert res.status_code == 400


def test_pharmacy_fefo_dispense_order(client, app):
    """Auto-FEFO dispensing must consume stock from the earliest-expiring batch first."""
    with app.app_context():
        clinic = Clinic(name="FEFO Clinic", currency="PKR")
        role = Role(name="Pharmacist")
        db.session.add_all([clinic, role])
        db.session.flush()

        user = User(username="fefo_user", email="fefo@clinic.com", clinic_id=clinic.id, is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

        med = Medicine(name="Paracetamol", clinic_id=clinic.id, base_price=Decimal("5.00"))
        db.session.add(med)
        db.session.flush()

        # Batch 1 expires in 10 days (qty 10)
        b1 = MedicineBatch(
            medicine_id=med.id,
            batch_number="LOT-EARLY",
            quantity_received=10,
            quantity_remaining=10,
            expiry_date=date.today() + timedelta(days=10),
        )
        # Batch 2 expires in 60 days (qty 20)
        b2 = MedicineBatch(
            medicine_id=med.id,
            batch_number="LOT-LATER",
            quantity_received=20,
            quantity_remaining=20,
            expiry_date=date.today() + timedelta(days=60),
        )
        db.session.add_all([b1, b2])
        db.session.commit()
        med_id = med.id

    client.post('/auth/login', data={'email': 'fefo@clinic.com', 'password': 'Pass123!'})

    # Dispense 15 units with batch_id=0 (Auto FEFO)
    # Should completely deplete b1 (10 units) and take 5 units from b2 (leaving 15 units)
    res = client.post(f'/pharmacy/{med_id}/dispense', data={
        'batch_id': 0,
        'quantity': 15,
        'notes': 'Auto FEFO dispense',
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        re_b1 = MedicineBatch.query.filter_by(batch_number="LOT-EARLY").first()
        re_b2 = MedicineBatch.query.filter_by(batch_number="LOT-LATER").first()
        assert re_b1.quantity_remaining == 0
        assert re_b2.quantity_remaining == 15


def test_appointment_doctor_conflict_rejected(client, app):
    """Overlapping appointment booking for the same doctor must return HTTP 400."""
    with app.app_context():
        clinic = Clinic(name="Conflict Clinic", currency="PKR")
        role = Role(name="Receptionist")
        doc_role = Role(name="Doctor")
        db.session.add_all([clinic, role, doc_role])
        db.session.flush()

        staff = User(username="rec1", email="rec1@conflict.com", clinic_id=clinic.id, is_active=True)
        staff.set_password("Pass123!")

        doc = User(username="dr_conflict", email="dr@conflict.com", clinic_id=clinic.id, is_active=True)
        doc.set_password("Pass123!")
        db.session.add_all([staff, doc])
        db.session.flush()

        db.session.add(UserRole(user_id=staff.id, role_id=role.id))
        db.session.add(UserRole(user_id=doc.id, role_id=doc_role.id))

        species = Species(name="Canine")
        db.session.add(species)
        db.session.flush()

        owner = Owner(
            first_name="Conflict",
            last_name="Owner",
            email="conflict@owner.com",
            phone="03009998877",
            clinic_id=clinic.id,
        )
        db.session.add(owner)
        db.session.flush()

        pet = Pet(name="Buddy", species_id=species.id, owner_id=owner.id)
        apt_type = AppointmentType(name="Checkup", duration_minutes=30, base_fee=Decimal("50.00"))
        db.session.add_all([pet, apt_type])
        db.session.commit()

        # Existing appointment from 10:00 to 10:30
        existing_apt = Appointment(
            pet_id=pet.id,
            doctor_id=doc.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type.id,
            appointment_date=date.today() + timedelta(days=2),
            appointment_time=time(10, 0),
            status='Scheduled',
        )
        db.session.add(existing_apt)
        db.session.commit()

        target_date = existing_apt.appointment_date
        doc_id = doc.id
        pet_id = pet.id
        type_id = apt_type.id
        clinic_id = clinic.id

    client.post('/auth/login', data={'email': 'rec1@conflict.com', 'password': 'Pass123!'})

    # Direct utility check (inside app context)
    with app.app_context():
        conflict = check_appointment_conflict(
            doctor_id=doc_id,
            appointment_date=target_date,
            appointment_time=time(10, 15),
            duration_minutes=30,
        )
        assert conflict is not None
        assert "Doctor schedule conflict" in conflict

    # Route POST check: overlapping at 10:15 (overlaps 10:00 - 10:30) -> must abort 400
    res = client.post('/appointments/new', data={
        'pet_id': pet_id,
        'doctor_id': doc_id,
        'clinic_id': clinic_id,
        'appointment_type_id': type_id,
        'appointment_date': target_date.strftime('%Y-%m-%d'),
        'appointment_time': '10:15',
        'reason': 'Overlapping visit',
    })
    assert res.status_code == 400
