from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Appointment,
    AuditLog,
    Clinic,
    Department,
    DoctorSchedule,
    Invoice,
    MedicalRecord,
    Medicine,
    Owner,
    Pet,
    Role,
    Room,
    User,
    log_activity,
)
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/recycle-bin')
@login_required
@admin_required
def recycle_bin():
    tab = request.args.get('tab', 'pets')

    counts = {
        'pets': Pet.query_deleted().count(),
        'owners': Owner.query_deleted().count(),
        'appointments': Appointment.query_deleted().count(),
        'invoices': Invoice.query_deleted().count(),
        'medicines': Medicine.query_deleted().count(),
        'records': MedicalRecord.query_deleted().count()
    }

    if tab == 'owners':
        items = Owner.query_deleted().order_by(Owner.deleted_at.desc()).all()
    elif tab == 'appointments':
        items = Appointment.query_deleted().order_by(Appointment.deleted_at.desc()).all()
    elif tab == 'invoices':
        items = Invoice.query_deleted().order_by(Invoice.deleted_at.desc()).all()
    elif tab == 'medicines':
        items = Medicine.query_deleted().order_by(Medicine.deleted_at.desc()).all()
    elif tab == 'records':
        items = MedicalRecord.query_deleted().order_by(MedicalRecord.deleted_at.desc()).all()
    else:
        tab = 'pets'
        items = Pet.query_deleted().order_by(Pet.deleted_at.desc()).all()

    # Preload deleter usernames
    deleter_ids = {item.deleted_by for item in items if item.deleted_by}
    deleters = {u.id: u.username for u in User.query.filter(User.id.in_(deleter_ids)).all()} if deleter_ids else {}

    return render_template(
        'admin/recycle_bin.html',
        items=items,
        counts=counts,
        current_tab=tab,
        deleters=deleters
    )


@admin_bp.route('/recycle-bin/restore/<model_name>/<int:id>', methods=['POST'])
@login_required
@admin_required
def restore_item(model_name, id):
    model_map = {
        'pet': Pet,
        'owner': Owner,
        'appointment': Appointment,
        'invoice': Invoice,
        'medicine': Medicine,
        'medical_record': MedicalRecord
    }
    model_cls = model_map.get(model_name.lower())
    if not model_cls:
        flash('Invalid entity type for restoration.', 'danger')
        return redirect(url_for('admin.recycle_bin'))

    item = model_cls.query_deleted().filter_by(id=id).first_or_404()
    item_label = getattr(item, 'name', None) or getattr(item, 'full_name', None) or getattr(item, 'invoice_number', f"#{item.id}")
    item.restore()
    log_activity('RESTORE', model_cls.__name__, item.id, f'Admin {current_user.username} restored {model_name} {item_label}')
    db.session.commit()

    flash(f'{model_name.replace("_", " ").title()} "{item_label}" restored successfully and returned to active queries!', 'success')
    return redirect(url_for('admin.recycle_bin', tab=model_name if model_name != 'medical_record' else 'records'))


@admin_bp.route('/recycle-bin/purge/<model_name>/<int:id>', methods=['POST'])
@login_required
@admin_required
def hard_delete_item(model_name, id):
    model_map = {
        'pet': Pet,
        'owner': Owner,
        'appointment': Appointment,
        'invoice': Invoice,
        'medicine': Medicine,
        'medical_record': MedicalRecord
    }
    model_cls = model_map.get(model_name.lower())
    if not model_cls:
        flash('Invalid entity type.', 'danger')
        return redirect(url_for('admin.recycle_bin'))

    item = model_cls.query_deleted().filter_by(id=id).first_or_404()
    item_label = getattr(item, 'name', None) or getattr(item, 'full_name', None) or f"#{item.id}"

    log_activity('PURGE', model_cls.__name__, item.id, f'Permanently deleted {model_name} {item_label}')
    db.session.delete(item)
    db.session.commit()

    flash(f'Permanently purged {model_name} "{item_label}" from the database.', 'info')
    return redirect(url_for('admin.recycle_bin', tab=model_name if model_name != 'medical_record' else 'records'))


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')

    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    actions = ['CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'LOGIN', 'LOGOUT', 'PURGE']

    return render_template(
        'admin/audit_logs.html',
        pagination=pagination,
        actions=actions,
        selected_action=action_filter
    )


@admin_bp.route('/staff')
@login_required
@admin_required
def staff():
    users = User.query_active().order_by(User.first_name).all()
    roles = Role.query_active().all()
    schedules = DoctorSchedule.query_active().all()
    return render_template('admin/staff.html', users=users, roles=roles, schedules=schedules)


@admin_bp.route('/clinics')
@login_required
@admin_required
def clinics():
    clinic_list = Clinic.query_active().all()
    departments = Department.query_active().all()
    rooms = Room.query_active().all()
    return render_template('admin/clinics.html', clinics=clinic_list, departments=departments, rooms=rooms)

