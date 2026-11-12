from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Appointment,
    Invoice,
    LabOrder,
    MedicalRecord,
    Medicine,
    MedicineBatch,
    Owner,
    Payment,
    Pet,
)
from app.utils.tenant import tenant_filter

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()

    # Core Metric Counters (tenant-scoped)
    total_pets = tenant_filter(Pet.query_active(), Pet).count()
    total_owners = tenant_filter(Owner.query_active(), Owner).count()

    # Today's appointments with eager loading (preventing N+1 queries in template)
    today_appointments = (
        tenant_filter(Appointment.query_active(), Appointment)
        .options(
            db.joinedload(Appointment.pet).joinedload(Pet.owner),
            db.joinedload(Appointment.pet).joinedload(Pet.species),
            db.joinedload(Appointment.doctor),
            db.joinedload(Appointment.appointment_type),
            db.joinedload(Appointment.queue_token),
        )
        .filter(Appointment.appointment_date == today)
        .order_by(Appointment.appointment_time.asc())
        .all()
    )

    # Pending Lab Orders
    pending_labs = tenant_filter(
        LabOrder.query_active().filter(LabOrder.status.in_(['Pending', 'Sample-Collected'])),
        LabOrder,
    ).count()

    # Low stock alerts - single optimized SQL aggregate query joining batches (eliminating N+1)
    batches_subq = (
        db.session.query(
            MedicineBatch.medicine_id,
            func.coalesce(func.sum(MedicineBatch.quantity_remaining), 0).label('total_qty'),
        )
        .filter(MedicineBatch.deleted_at.is_(None))
        .group_by(MedicineBatch.medicine_id)
        .subquery()
    )

    low_stock_rows = (
        tenant_filter(Medicine.query_active(), Medicine)
        .outerjoin(batches_subq, Medicine.id == batches_subq.c.medicine_id)
        .filter(Medicine.minimum_stock > 0)
        .filter(func.coalesce(batches_subq.c.total_qty, 0) <= Medicine.minimum_stock)
        .add_columns(func.coalesce(batches_subq.c.total_qty, 0).label('qty'))
        .all()
    )
    alert_medicines = [{'med': row[0], 'qty': int(row[1])} for row in low_stock_rows]

    # Recent Medical Visits with eager loaded pet and doctor
    recent_records = (
        tenant_filter(MedicalRecord.query_active(), MedicalRecord)
        .options(
            db.joinedload(MedicalRecord.pet).joinedload(Pet.owner),
            db.joinedload(MedicalRecord.doctor),
        )
        .order_by(MedicalRecord.visit_date.desc())
        .limit(6)
        .all()
    )

    # Financial overview calculated via SQL aggregate (no in-memory summation)
    revenue_today = (
        db.session.query(func.coalesce(func.sum(Payment.amount), Decimal('0.00')))
        .filter(Payment.deleted_at.is_(None))
        .filter(func.date(Payment.payment_date) == today)
        .scalar()
    ) or Decimal('0.00')

    unpaid_invoices_count = tenant_filter(
        Invoice.query_active().filter(Invoice.status.in_(['Draft', 'Unpaid', 'Partially-Paid'])),
        Invoice,
    ).count()

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
        today_date=today,
    )


@dashboard_bp.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('dashboard/search.html', q=q, owners=[], pets=[])

    search_filter = f"%{q}%"
    owners = (
        tenant_filter(Owner.query_active(), Owner)
        .filter(
            (Owner.first_name.ilike(search_filter))
            | (Owner.last_name.ilike(search_filter))
            | (Owner.phone.ilike(search_filter))
            | (Owner.email.ilike(search_filter))
        )
        .limit(20)
        .all()
    )

    pets = (
        tenant_filter(Pet.query_active(), Pet)
        .filter(
            (Pet.name.ilike(search_filter))
            | (Pet.microchip_number.ilike(search_filter))
            | (Pet.color.ilike(search_filter))
        )
        .limit(20)
        .all()
    )

    return render_template('dashboard/search.html', q=q, owners=owners, pets=pets)

