from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
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
    QueueToken,
)
from app.utils.tenant import tenant_filter

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()

    # Persona 1: User / Pet Owner Client Portal
    if current_user.has_role('User'):
        owner = current_user.owner_profile
        pets = [p for p in owner.pets if not p.is_deleted] if owner else []
        pet_ids = [p.id for p in pets]

        upcoming_appointments = []
        medical_records = []
        invoices = []

        if pet_ids:
            upcoming_appointments = (
                tenant_filter(Appointment.query_active(), Appointment)
                .options(
                    db.joinedload(Appointment.pet),
                    db.joinedload(Appointment.doctor),
                )
                .filter(Appointment.pet_id.in_(pet_ids))
                .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
                .limit(10)
                .all()
            )
            medical_records = (
                tenant_filter(MedicalRecord.query_active(), MedicalRecord)
                .options(
                    db.joinedload(MedicalRecord.pet),
                    db.joinedload(MedicalRecord.doctor),
                )
                .filter(MedicalRecord.pet_id.in_(pet_ids))
                .order_by(MedicalRecord.visit_date.desc())
                .limit(10)
                .all()
            )

        if owner:
            invoices = (
                tenant_filter(Invoice.query_active(), Invoice)
                .filter(Invoice.owner_id == owner.id)
                .order_by(Invoice.created_at.desc())
                .limit(10)
                .all()
            )

        return render_template(
            'dashboard/user_portal.html',
            owner=owner,
            pets=pets,
            upcoming_appointments=upcoming_appointments,
            medical_records=medical_records,
            invoices=invoices,
        )

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

    # Active Queue Tokens for today (with eager loading to avoid N+1 queries)
    queue_tokens = (
        tenant_filter(QueueToken.query, QueueToken)
        .options(
            db.joinedload(QueueToken.appointment).joinedload(Appointment.pet).joinedload(Pet.owner)
        )
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(Appointment.appointment_date == today)
        .filter(QueueToken.status.in_(['Issued', 'Called']))
        .order_by(QueueToken.issued_at.asc())
        .all()
    )

    # Persona 2: Doctor Cockpit
    if current_user.has_role('Doctor'):
        doc_today_appointments = [a for a in today_appointments if a.doctor_id == current_user.id]
        if not doc_today_appointments:
            doc_today_appointments = today_appointments

        doc_recent_records = (
            tenant_filter(MedicalRecord.query_active(), MedicalRecord)
            .options(
                db.joinedload(MedicalRecord.pet),
                db.joinedload(MedicalRecord.doctor),
            )
            .filter(MedicalRecord.doctor_id == current_user.id)
            .order_by(MedicalRecord.visit_date.desc())
            .limit(6)
            .all()
        )
        if not doc_recent_records:
            doc_recent_records = recent_records

        return render_template(
            'dashboard/doctor_dashboard.html',
            today_date=today,
            today_appointments=doc_today_appointments,
            queue_tokens=queue_tokens,
            pending_labs=pending_labs,
            recent_records=doc_recent_records,
        )

    # Persona 3: Staff / Receptionist Cockpit
    if current_user.has_role('Staff') or current_user.has_role('Receptionist'):
        return render_template(
            'dashboard/staff_dashboard.html',
            today_date=today,
            today_appointments=today_appointments,
            today_appointments_count=len(today_appointments),
            queue_tokens=queue_tokens,
            unpaid_invoices_count=unpaid_invoices_count,
            alert_medicines=alert_medicines,
        )

    # Persona 4: Admin Executive Overview (Default)
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

