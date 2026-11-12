from datetime import UTC, date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.appointments import AppointmentForm, StatusUpdateForm
from app.models import (
    Appointment,
    AppointmentStatusHistory,
    AppointmentType,
    Clinic,
    Pet,
    QueueToken,
    User,
    log_activity,
)
from app.utils.appointments import check_appointment_conflict
from app.utils.decorators import staff_required
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')


@appointments_bp.route('/')
@login_required
def index():
    filter_mode = request.args.get('filter', 'today')  # today, upcoming, past, all
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    today = date.today()
    query = tenant_filter(Appointment.query_active(), Appointment)

    if filter_mode == 'today':
        query = query.filter(Appointment.appointment_date == today)
    elif filter_mode == 'upcoming':
        query = query.filter(Appointment.appointment_date >= today)
    elif filter_mode == 'past':
        query = query.filter(Appointment.appointment_date < today)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    pagination = query.order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc()).paginate(
        page=page, per_page=15, error_out=False
    )

    return render_template(
        'appointments/index.html',
        pagination=pagination,
        filter_mode=filter_mode,
        status_filter=status_filter,
        today=today
    )


@appointments_bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    form = AppointmentForm()

    # Populate dropdown choices
    form.pet_id.choices = [(p.id, f"{p.name} ({p.species.name} - Owner: {p.owner.full_name})") for p in Pet.query_active().all()]
    
    # Load doctors
    doctors = [u for u in User.query_active().all() if u.has_role('Doctor') or u.has_role('Admin')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name}") for d in doctors]
    
    form.clinic_id.choices = [(c.id, c.name) for c in Clinic.query_active().all()]
    form.appointment_type_id.choices = [(t.id, f"{t.name} (PKR {t.base_fee:.2f})") for t in AppointmentType.query_active().all()]

    # Pre-select pet if passed in query param
    pre_pet = request.args.get('pet_id', type=int)
    if pre_pet and request.method == 'GET':
        form.pet_id.data = pre_pet

    if form.validate_on_submit():
        apt_type = db.session.get(AppointmentType, form.appointment_type_id.data)
        duration = apt_type.duration_minutes if apt_type else 30
        conflict = check_appointment_conflict(
            doctor_id=form.doctor_id.data,
            appointment_date=form.appointment_date.data,
            appointment_time=form.appointment_time.data,
            duration_minutes=duration,
        )
        if conflict:
            abort(400, description=conflict)

        appointment = Appointment(
            pet_id=form.pet_id.data,
            doctor_id=form.doctor_id.data,
            clinic_id=get_current_tenant_id() or form.clinic_id.data,
            appointment_type_id=form.appointment_type_id.data,
            appointment_date=form.appointment_date.data,
            appointment_time=form.appointment_time.data,
            reason=form.reason.data,
            notes=form.notes.data,
            status='Scheduled',
            created_by=current_user.id
        )
        db.session.add(appointment)
        db.session.flush()

        # Generate Queue Token for the day
        count_today = QueueToken.query.filter(
            db.func.date(QueueToken.issued_at) == appointment.appointment_date
        ).count()
        token_num = f"Q-{(count_today + 1):03d}"

        token = QueueToken(
            appointment_id=appointment.id,
            token_number=token_num,
            status='Waiting'
        )
        db.session.add(token)

        # Record Initial Status History
        history = AppointmentStatusHistory(
            appointment_id=appointment.id,
            old_status=None,
            new_status='Scheduled',
            changed_by=current_user.id,
            notes='Initial appointment scheduled'
        )
        db.session.add(history)

        log_activity('CREATE', 'Appointment', appointment.id, f'Booked appointment for pet ID {appointment.pet_id} with Dr. ID {appointment.doctor_id}')
        db.session.commit()

        flash(f'Appointment booked successfully! Queue Token #{token_num} issued.', 'success')
        return redirect(url_for('appointments.view', id=appointment.id))

    return render_template('appointments/form.html', form=form, title='Book New Appointment')


@appointments_bp.route('/<int:id>')
@login_required
def view(id):
    appointment = Appointment.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(appointment)
    status_form = StatusUpdateForm()
    status_form.new_status.data = appointment.status
    return render_template('appointments/view.html', appointment=appointment, status_form=status_form)


@appointments_bp.route('/<int:id>/status', methods=['POST'])
@login_required
@staff_required
def update_status(id):
    appointment = Appointment.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(appointment)
    form = StatusUpdateForm()
    if form.validate_on_submit():
        old_stat = appointment.status
        new_stat = form.new_status.data

        if old_stat != new_stat:
            appointment.status = new_stat
            
            # Sync Queue Token status if exists
            if appointment.queue_token:
                if new_stat == 'In-Consultation':
                    appointment.queue_token.status = 'Serving'
                    appointment.queue_token.called_at = datetime.now(UTC)
                elif new_stat == 'Completed':
                    appointment.queue_token.status = 'Completed'
                    appointment.queue_token.completed_at = datetime.now(UTC)
                elif new_stat in ['Cancelled', 'No-Show']:
                    appointment.queue_token.status = 'Cancelled'

            # Record Status History
            history = AppointmentStatusHistory(
                appointment_id=appointment.id,
                old_status=old_stat,
                new_status=new_stat,
                changed_by=current_user.id,
                notes=form.notes.data
            )
            db.session.add(history)
            log_activity('UPDATE', 'Appointment', appointment.id, f'Changed status from {old_stat} to {new_stat}')
            db.session.commit()
            flash(f'Appointment status changed to {new_stat}.', 'success')

    return redirect(url_for('appointments.view', id=appointment.id))


@appointments_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete(id):
    appointment = Appointment.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(appointment)
    appointment.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'Appointment', appointment.id, f'Soft-deleted appointment #{appointment.id}')
    db.session.commit()

    flash(f'Appointment #{appointment.id} moved to Recycle Bin.', 'warning')
    return redirect(url_for('appointments.index'))

