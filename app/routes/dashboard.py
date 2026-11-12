from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required

from app.extensions import db
from app.models import (
    Appointment,
    Invoice,
    LabOrder,
    MedicalRecord,
    Medicine,
    Owner,
    Payment,
    Pet,
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()

    # Core Metric Counters (all query_active)
    total_pets = Pet.query_active().count()
    total_owners = Owner.query_active().count()
    
    # Today's appointments
    today_appointments = Appointment.query_active().filter(
        Appointment.appointment_date == today
    ).order_by(Appointment.appointment_time.asc()).all()

    # Pending Lab Orders
    pending_labs = LabOrder.query_active().filter(LabOrder.status.in_(['Pending', 'Sample-Collected'])).count()

    # Low stock alerts
    low_stock_medicines = Medicine.query_active().filter(Medicine.minimum_stock > 0).all()
    # Filter medicines where sum of remaining batches <= min_stock
    alert_medicines = []
    for med in low_stock_medicines:
        total_qty = sum(b.quantity_remaining for b in med.batches if not b.is_deleted)
        if total_qty <= med.minimum_stock:
            alert_medicines.append({'med': med, 'qty': total_qty})

    # Recent Medical Visits
    recent_records = MedicalRecord.query_active().order_by(MedicalRecord.visit_date.desc()).limit(6).all()

    # Financial overview
    today_payments = Payment.query_active().filter(
        db.func.date(Payment.payment_date) == today
    ).all()
    revenue_today = sum(p.amount for p in today_payments)

    unpaid_invoices_count = Invoice.query_active().filter(Invoice.status.in_(['Draft', 'Unpaid', 'Partially-Paid'])).count()

    return render_template(
        'dashboard/index.html',
        total_pets=total_pets,
        total_owners=total_owners,
        today_appointments=today_appointments,
        today_appointments_count=len(today_appointments),
        pending_labs=pending_labs,
        alert_medicines=alert_medicines,
        recent_records=recent_records,
        revenue_today=revenue_today,
        unpaid_invoices_count=unpaid_invoices_count,
        today_date=today
    )

