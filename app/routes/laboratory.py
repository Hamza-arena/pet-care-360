from datetime import UTC, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.laboratory import LabOrderForm, LabResultForm, SurgeryForm
from app.models import (
    LabOrder,
    LabOrderItem,
    LabResult,
    LabTest,
    Pet,
    Room,
    Surgery,
    User,
    log_activity,
)
from app.utils.decorators import doctor_required, staff_required
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

laboratory_bp = Blueprint('laboratory', __name__, url_prefix='/lab')


@laboratory_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = tenant_filter(LabOrder.query_active(), LabOrder)
    if status_filter:
        query = query.filter(LabOrder.status == status_filter)

    pagination = query.order_by(LabOrder.order_date.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('laboratory/index.html', pagination=pagination, selected_status=status_filter)


@laboratory_bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_order():
    form = LabOrderForm()
    form.pet_id.choices = [(p.id, f"{p.name} ({p.species.name} - Owner: {p.owner.full_name})") for p in Pet.query_active().all()]
    doctors = [u for u in User.query_active().all() if u.has_role('Doctor') or u.has_role('Admin')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name}") for d in doctors]
    form.lab_test_id.choices = [(t.id, f"{t.name} ({t.category} - PKR {t.base_price:.2f})") for t in LabTest.query_active().all()]

    pre_pet = request.args.get('pet_id', type=int)
    if pre_pet and request.method == 'GET':
        form.pet_id.data = pre_pet

    if form.validate_on_submit():
        order = LabOrder(
            clinic_id=get_current_tenant_id(),
            pet_id=form.pet_id.data,
            doctor_id=form.doctor_id.data,
            priority=form.priority.data,
            status='Pending',
            notes=form.notes.data,
            order_date=datetime.now(UTC)
        )
        db.session.add(order)
        db.session.flush()

        # Add initial order item
        item = LabOrderItem(
            lab_order_id=order.id,
            lab_test_id=form.lab_test_id.data,
            status='Pending'
        )
        db.session.add(item)
        log_activity('CREATE', 'LabOrder', order.id, f'Placed lab order #{order.id} for Pet ID {order.pet_id}')
        db.session.commit()

        flash(f'Lab order #{order.id} placed successfully.', 'success')
        return redirect(url_for('laboratory.view_order', id=order.id))

    return render_template('laboratory/order_form.html', form=form)


@laboratory_bp.route('/orders/<int:id>')
@login_required
def view_order(id):
    order = LabOrder.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(order)
    result_form = LabResultForm()
    return render_template('laboratory/view_order.html', order=order, result_form=result_form)


@laboratory_bp.route('/items/<int:item_id>/result', methods=['POST'])
@login_required
@staff_required
def record_result(item_id):
    item = LabOrderItem.query.filter_by(id=item_id).first_or_404()
    form = LabResultForm()
    if form.validate_on_submit():
        result = item.result
        if not result:
            result = LabResult(lab_order_item_id=item.id)
            db.session.add(result)

        result.result_value = form.result_value.data
        result.result_text = form.result_text.data
        result.is_abnormal = form.is_abnormal.data
        result.notes = form.notes.data
        result.performed_by = current_user.id
        result.verified_by = current_user.id
        result.result_date = datetime.now(UTC)

        item.status = 'Completed'
        item.lab_order.status = 'Completed'

        log_activity('UPDATE', 'LabResult', result.id, f'Recorded lab result for Order #{item.lab_order_id}')
        db.session.commit()

        flash('Laboratory test result recorded successfully.', 'success')

    return redirect(url_for('laboratory.view_order', id=item.lab_order_id))


@laboratory_bp.route('/surgeries')
@login_required
def surgeries():
    page = request.args.get('page', 1, type=int)
    pagination = Surgery.query_active().order_by(Surgery.scheduled_date.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('laboratory/surgeries.html', pagination=pagination)


@laboratory_bp.route('/surgeries/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_surgery():
    form = SurgeryForm()
    form.pet_id.choices = [(p.id, f"{p.name} ({p.species.name} - Owner: {p.owner.full_name})") for p in Pet.query_active().all()]
    doctors = [u for u in User.query_active().all() if u.has_role('Doctor') or u.has_role('Admin')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name}") for d in doctors]
    rooms = Room.query_active().all()
    form.room_id.choices = [(0, '-- Any Available OR --')] + [(r.id, f"{r.room_number} ({r.room_type or 'Room'})") for r in rooms]

    pre_pet = request.args.get('pet_id', type=int)
    if pre_pet and request.method == 'GET':
        form.pet_id.data = pre_pet

    if form.validate_on_submit():
        surgery = Surgery(
            pet_id=form.pet_id.data,
            doctor_id=form.doctor_id.data,
            room_id=form.room_id.data if form.room_id.data and form.room_id.data > 0 else None,
            surgery_type=form.surgery_type.data.strip(),
            scheduled_date=form.scheduled_date.data,
            description=form.description.data,
            anesthesia_type=form.anesthesia_type.data,
            status='Scheduled'
        )
        db.session.add(surgery)
        log_activity('CREATE', 'Surgery', surgery.id, f'Scheduled surgery "{surgery.surgery_type}" for Pet ID {surgery.pet_id}')
        db.session.commit()

        flash(f'Surgery "{surgery.surgery_type}" scheduled successfully.', 'success')
        return redirect(url_for('laboratory.surgeries'))

    return render_template('laboratory/surgery_form.html', form=form)

