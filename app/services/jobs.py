import logging
import time
from datetime import UTC, date, datetime, timedelta
from functools import wraps

from app.extensions import db
from app.models.appointments import Appointment, AppointmentStatusHistory
from app.models.clinic import Clinic
from app.models.finance import Invoice
from app.models.pharmacy import Medicine
from app.models.vaccination import VaccinationReminder
from app.services.notifications import get_notification_service

logger = logging.getLogger('petcare360.jobs')


def retry_job(max_attempts=3, backoff_base=0.1):
    """Decorator to retry transient failures up to max_attempts with exponential backoff."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    last_exception = e
                    logger.warning(
                        f"Job {fn.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                    )
                    if attempt < max_attempts:
                        delay = backoff_base * (2 ** (attempt - 1))
                        time.sleep(delay)
            logger.error(f"Job {fn.__name__} exhausted all {max_attempts} attempts. Final error: {last_exception}")
            raise last_exception
        return wrapper
    return decorator


@retry_job(max_attempts=3, backoff_base=0.05)
def send_appointment_reminder_notification(appointment, notifier):
    """Dispatch an appointment reminder with retry."""
    if not appointment.pet or not appointment.pet.owner:
        return False

    owner = appointment.pet.owner
    email = owner.email
    if not email:
        return False

    pet_name = appointment.pet.name
    doc_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}" if appointment.doctor else "our veterinary team"
    apt_time_str = appointment.appointment_time.strftime('%I:%M %p')
    apt_date_str = appointment.appointment_date.strftime('%A, %B %d')

    subject = f"Appointment Reminder for {pet_name} - PetCare 360"
    body = (
        f"Dear {owner.first_name},\n\n"
        f"This is a friendly reminder that {pet_name} has an appointment scheduled with {doc_name} "
        f"on {apt_date_str} at {apt_time_str}.\n\n"
        f"Please arrive 10 minutes early. If you need to reschedule, please contact the clinic.\n\n"
        f"Best regards,\nPetCare 360 Team"
    )

    return notifier.send_email(to=email, subject=subject, body=body)


def process_appointment_reminders(reference_now=None):
    """Scan appointments scheduled within the next 24 hours and send reminder notifications.

    Only targets appointments with status 'Scheduled' that have not yet had a reminder dispatched.
    """
    now = reference_now or datetime.now(UTC)
    now_date = now.date()
    target_end_date = now_date + timedelta(days=1)

    appointments = Appointment.query_active().filter(
        Appointment.status == 'Scheduled',
        Appointment.appointment_date >= now_date,
        Appointment.appointment_date <= target_end_date,
    ).all()

    notifier = get_notification_service()
    sent_count = 0

    for apt in appointments:
        # Check if reminder was already sent
        already_sent = any(
            h.notes and 'Appointment Reminder Dispatched' in h.notes
            for h in apt.status_history
        )
        if already_sent:
            continue

        success = send_appointment_reminder_notification(apt, notifier)
        if success:
            history = AppointmentStatusHistory(
                appointment_id=apt.id,
                old_status=apt.status,
                new_status=apt.status,
                notes='24h Appointment Reminder Dispatched',
            )
            db.session.add(history)
            sent_count += 1

    db.session.commit()
    logger.info(f"Processed appointment reminders: {sent_count} dispatched.")
    return sent_count


def process_low_stock_alerts():
    """Identify medicines at or below minimum reorder threshold and send daily digest to clinic admins."""
    notifier = get_notification_service()
    clinics = Clinic.query_active().all()
    alerts_dispatched = 0

    for clinic in clinics:
        meds = Medicine.query_active().filter(Medicine.clinic_id == clinic.id).all()
        low_stock_items = []
        for m in meds:
            total_stock = sum(b.quantity_remaining for b in m.batches if not b.is_deleted)
            if total_stock <= m.minimum_stock:
                low_stock_items.append((m, total_stock))

        if not low_stock_items or not clinic.email:
            continue

        subject = f"Daily Inventory Low-Stock Alert: {clinic.name}"
        lines = [
            f"Dear Clinic Administrator,\n\nThe following medications are below minimum threshold in {clinic.name}:\n"
        ]
        for med, stock in low_stock_items:
            lines.append(f"- {med.name} ({med.unit}): Current Stock = {stock}, Minimum Required = {med.minimum_stock}")
        lines.append("\nPlease review your pharmacy inventory and place replenishment orders.\n\nPetCare 360 Inventory Monitor")

        body = "\n".join(lines)
        notifier.send_email(to=clinic.email, subject=subject, body=body)
        alerts_dispatched += 1

    return alerts_dispatched


def process_vaccination_reminders(target_date=None):
    """Scan pending vaccination reminders due on or before target_date and notify owners."""
    check_date = target_date or (date.today() + timedelta(days=7))
    notifier = get_notification_service()

    reminders = VaccinationReminder.query.filter(
        VaccinationReminder.status == 'Pending',
        VaccinationReminder.reminder_date <= check_date,
    ).all()

    dispatched = 0
    for rem in reminders:
        pet = rem.pet
        if not pet or not pet.owner or not pet.owner.email:
            continue

        subject = f"Vaccination Due Reminder for {pet.name} - PetCare 360"
        vaccine_name = rem.vaccine.name if rem.vaccine else "Routine Immunization"
        body = (
            f"Dear {pet.owner.first_name},\n\n"
            f"This is a reminder that {pet.name} is due for their {vaccine_name} vaccination on "
            f"{rem.reminder_date.strftime('%B %d, %Y')}.\n\n"
            f"Keeping vaccinations up-to-date protects your pet from preventable diseases. "
            f"Please visit our clinic or book an appointment online.\n\n"
            f"Best regards,\nPetCare 360 Team"
        )

        notifier.send_email(to=pet.owner.email, subject=subject, body=body)
        rem.status = 'Sent'
        rem.sent_at = datetime.now(UTC)
        dispatched += 1

    db.session.commit()
    logger.info(f"Processed vaccination reminders: {dispatched} dispatched.")
    return dispatched


def process_overdue_invoice_reminders(today=None):
    """Scan unpaid invoices that have passed their due date and dispatch payment reminders."""
    cur_date = today or date.today()
    notifier = get_notification_service()

    overdue_invoices = Invoice.query_active().filter(
        Invoice.status.in_(['Draft', 'Unpaid', 'Partially-Paid']),
        Invoice.due_date < cur_date,
    ).all()

    dispatched = 0
    for inv in overdue_invoices:
        if not inv.owner or not inv.owner.email:
            continue

        currency = inv.clinic.currency if inv.clinic and getattr(inv.clinic, 'currency', None) else 'PKR'
        subject = f"Payment Reminder: Invoice #{inv.invoice_number} is Overdue"
        body = (
            f"Dear {inv.owner.first_name},\n\n"
            f"This is a payment notice that Invoice #{inv.invoice_number} for {currency} {inv.balance_due:.2f} "
            f"was due on {inv.due_date.strftime('%B %d, %Y')}.\n\n"
            f"Please arrange payment at your earliest convenience.\n\n"
            f"Thank you,\nPetCare 360 Accounts"
        )
        notifier.send_email(to=inv.owner.email, subject=subject, body=body)
        dispatched += 1

    return dispatched


def run_all_scheduled_jobs():
    """Master job runner executing all scheduled background tasks."""
    logger.info("Executing scheduled PetCare 360 background jobs...")
    apt_count = process_appointment_reminders()
    inv_count = process_low_stock_alerts()
    vac_count = process_vaccination_reminders()
    overdue_count = process_overdue_invoice_reminders()

    summary = {
        'appointment_reminders': apt_count,
        'low_stock_alerts': inv_count,
        'vaccination_reminders': vac_count,
        'overdue_invoice_reminders': overdue_count,
    }
    logger.info(f"Background jobs completed: {summary}")
    return summary

