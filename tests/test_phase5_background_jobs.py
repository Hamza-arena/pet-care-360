from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.appointments import Appointment, AppointmentType
from app.models.auth import User
from app.models.clinic import Clinic
from app.models.finance import Invoice
from app.models.owners import Owner
from app.models.pets import Pet, Species
from app.models.pharmacy import Medicine, MedicineBatch
from app.models.vaccination import VaccinationReminder, VaccineCatalog
from app.services.jobs import (
    process_appointment_reminders,
    process_low_stock_alerts,
    process_overdue_invoice_reminders,
    process_vaccination_reminders,
    retry_job,
)
from app.services.notifications import (
    ConsoleNotificationService,
    get_notification_service,
)


@pytest.fixture(autouse=True)
def clean_outbox(app):
    """Ensure ConsoleNotificationService outbox is cleared before each test."""
    ConsoleNotificationService.clear()
    yield
    ConsoleNotificationService.clear()


def test_console_notification_service_send():
    """Verify ConsoleNotificationService captures emails and SMS in outbox."""
    service = get_notification_service()
    assert isinstance(service, ConsoleNotificationService)

    ok_email = service.send_email(
        to='owner@example.com',
        subject='Vaccine Due',
        body='Your pet needs rabies shot.'
    )
    assert ok_email is True
    assert len(service.outbox) == 1
    assert service.outbox[0]['to'] == 'owner@example.com'
    assert service.outbox[0]['subject'] == 'Vaccine Due'

    ok_sms = service.send_sms(
        to='+923001234567',
        message='Appointment tomorrow at 10 AM'
    )
    assert ok_sms is True
    assert len(service.sms_outbox) == 1
    assert service.sms_outbox[0]['to'] == '+923001234567'


def test_retry_job_transient_failure_recovery():
    """Verify retry_job retries and succeeds if a later attempt passes."""
    call_count = {'attempts': 0}

    @retry_job(max_attempts=3, backoff_base=0.01)
    def flaky_task():
        call_count['attempts'] += 1
        if call_count['attempts'] < 3:
            raise ValueError('Temporary network glitch')
        return 'success'

    result = flaky_task()
    assert result == 'success'
    assert call_count['attempts'] == 3


def test_retry_job_exhaustion_raises():
    """Verify retry_job raises exception when all attempts fail."""
    call_count = {'attempts': 0}

    @retry_job(max_attempts=2, backoff_base=0.01)
    def broken_task():
        call_count['attempts'] += 1
        raise ConnectionError('Persistent outage')

    with pytest.raises(ConnectionError, match='Persistent outage'):
        broken_task()
    assert call_count['attempts'] == 2


def test_appointment_reminders_and_idempotency(app):
    """Verify appointment reminders are sent for upcoming appointments and are idempotent."""
    with app.app_context():
        clinic = Clinic(name='Reminder Clinic', email='clinic@rem.com', is_active=True)
        db.session.add(clinic)
        db.session.flush()

        owner = Owner(
            clinic_id=clinic.id,
            first_name='Zain',
            last_name='Khan',
            phone='03001234567',
            email='zain@example.com',
        )
        db.session.add(owner)
        db.session.flush()

        species = Species(name='Canine-Jobs')
        db.session.add(species)
        db.session.flush()

        pet = Pet(owner_id=owner.id, species_id=species.id, name='Bruno')
        db.session.add(pet)
        db.session.flush()

        now = datetime.now(UTC)
        tomorrow = (now + timedelta(days=1)).date()

        doctor = User(username='dr_reminder', email='dr_reminder@test.com', clinic_id=clinic.id, is_active=True)
        doctor.set_password('Pass123!')
        apt_type = AppointmentType(name='Checkup', duration_minutes=30, base_fee=Decimal('500.00'))
        db.session.add_all([doctor, apt_type])
        db.session.flush()

        apt = Appointment(
            clinic_id=clinic.id,
            pet_id=pet.id,
            doctor_id=doctor.id,
            appointment_type_id=apt_type.id,
            appointment_date=tomorrow,
            appointment_time=now.time(),
            status='Scheduled',
            reason='Routine Checkup'
        )
        db.session.add(apt)
        db.session.commit()

        # Run reminder job
        sent = process_appointment_reminders(reference_now=now)
        assert sent == 1

        service = get_notification_service()
        assert len(service.outbox) == 1
        assert service.outbox[0]['to'] == 'zain@example.com'
        assert 'Bruno' in service.outbox[0]['subject']

        # Run again - idempotency check (should NOT dispatch duplicate reminder)
        sent_again = process_appointment_reminders(reference_now=now)
        assert sent_again == 0
        assert len(service.outbox) == 1


def test_low_stock_alerts(app):
    """Verify daily low-stock alerts notify clinic email when stock is below threshold."""
    with app.app_context():
        clinic = Clinic(name='Stock Alert Clinic', email='alerts@stockclinic.com', is_active=True)
        db.session.add(clinic)
        db.session.flush()

        med = Medicine(
            clinic_id=clinic.id,
            name='Amoxicillin 250mg',
            unit='Capsules',
            minimum_stock=20,
            base_price=Decimal('15.00'),
        )
        db.session.add(med)
        db.session.flush()

        # Add batch with quantity 5 (below minimum 20)
        batch = MedicineBatch(
            medicine_id=med.id,
            batch_number='AMX-LOW',
            quantity_received=5,
            quantity_remaining=5,
            expiry_date=date.today() + timedelta(days=90),
            purchase_price=Decimal('10.00'),
            selling_price=Decimal('15.00'),
        )
        db.session.add(batch)
        db.session.commit()

        alerts = process_low_stock_alerts()
        assert alerts == 1

        service = get_notification_service()
        assert len(service.outbox) == 1
        msg = service.outbox[0]
        assert msg['to'] == 'alerts@stockclinic.com'
        assert 'Amoxicillin 250mg' in msg['body']
        assert 'Current Stock = 5' in msg['body']


def test_vaccination_reminders(app):
    """Verify vaccination reminder sends email and transitions status to Sent."""
    with app.app_context():
        clinic = Clinic(name='Vax Clinic', email='vax@clinic.com', is_active=True)
        db.session.add(clinic)
        db.session.flush()

        owner = Owner(
            clinic_id=clinic.id,
            first_name='Fatima',
            last_name='Ali',
            phone='03009998877',
            email='fatima@vaxowner.com',
        )
        db.session.add(owner)
        db.session.flush()

        species = Species(name='Feline-Jobs')
        db.session.add(species)
        db.session.flush()

        pet = Pet(owner_id=owner.id, species_id=species.id, name='Milo')
        db.session.add(pet)
        db.session.flush()

        vaccine = VaccineCatalog(name='Rabies Core')
        db.session.add(vaccine)
        db.session.flush()

        rem = VaccinationReminder(
            pet_id=pet.id,
            vaccine_id=vaccine.id,
            reminder_date=date.today() + timedelta(days=3),
            status='Pending'
        )
        db.session.add(rem)
        db.session.commit()

        count = process_vaccination_reminders()
        assert count == 1

        # Check DB updated
        db.session.refresh(rem)
        assert rem.status == 'Sent'
        assert rem.sent_at is not None

        service = get_notification_service()
        assert len(service.outbox) == 1
        assert service.outbox[0]['to'] == 'fatima@vaxowner.com'
        assert 'Rabies Core' in service.outbox[0]['body']


def test_overdue_invoice_reminders(app):
    """Verify overdue unpaid invoices trigger payment reminders."""
    with app.app_context():
        clinic = Clinic(name='Billing Clinic', email='bills@clinic.com', currency='PKR', is_active=True)
        db.session.add(clinic)
        db.session.flush()

        owner = Owner(
            clinic_id=clinic.id,
            first_name='Tariq',
            last_name='Mahmood',
            phone='03215554433',
            email='tariq@overdue.com',
        )
        db.session.add(owner)
        db.session.flush()

        inv = Invoice(
            clinic_id=clinic.id,
            owner_id=owner.id,
            invoice_number='INV-OD-001',
            status='Unpaid',
            issue_date=datetime.now(UTC) - timedelta(days=15),
            due_date=date.today() - timedelta(days=5),
            subtotal=Decimal('2500.00'),
            total_amount=Decimal('2500.00'),
            paid_amount=Decimal('0.00'),
        )
        db.session.add(inv)
        db.session.commit()

        sent = process_overdue_invoice_reminders()
        assert sent == 1

        service = get_notification_service()
        assert len(service.outbox) == 1
        assert service.outbox[0]['to'] == 'tariq@overdue.com'
        assert 'INV-OD-001' in service.outbox[0]['subject']
        assert 'PKR 2500.00' in service.outbox[0]['body']


def test_cli_job_commands(app):
    """Verify CLI commands run-jobs, send-reminders, and check-inventory-alerts execute cleanly."""
    runner = app.test_cli_runner()

    res1 = runner.invoke(args=['run-jobs'])
    assert res1.exit_code == 0
    assert 'Executed all scheduled jobs' in res1.output

    res2 = runner.invoke(args=['send-reminders', '--job', 'all'])
    assert res2.exit_code == 0
    assert 'Appointment reminders dispatched' in res2.output

    res3 = runner.invoke(args=['check-inventory-alerts'])
    assert res3.exit_code == 0
    assert 'Low-stock alert digests dispatched' in res3.output

