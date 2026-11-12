from datetime import UTC, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.medical import MedicalRecordForm, PrescriptionItemForm
from app.models import (
    Appointment,
    Diagnosis,
    MedicalRecord,
    MedicalRecordDiagnosis,
    Medicine,
    Pet,
    Prescription,
    PrescriptionItem,
    Treatment,
    log_activity,
)
from app.utils.decorators import doctor_required
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

medical_bp = Blueprint('medical', __name__, url_prefix='/medical')


@medical_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()

    query = tenant_filter(MedicalRecord.query_active(), MedicalRecord)
    if search_q:
        search_filter = f"%{search_q}%"
        query = query.join(Pet).filter(
            (Pet.name.ilike(search_filter)) |
            (MedicalRecord.chief_complaint.ilike(search_filter))
        )

    pagination = query.order_by(MedicalRecord.visit_date.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('medical/index.html', pagination=pagination, search_q=search_q)


@medical_bp.route('/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def create():
    pet_id = request.args.get('pet_id', type=int)
    appointment_id = request.args.get('appointment_id', type=int)

    if not pet_id and appointment_id:
        apt = Appointment.query_active().filter_by(id=appointment_id).first()
        if apt:
            pet_id = apt.pet_id

    pet = Pet.query_active().filter_by(id=pet_id).first_or_404() if pet_id else None

    form = MedicalRecordForm()
    diagnoses = Diagnosis.query_active().order_by(Diagnosis.name).all()
    form.diagnosis_id.choices = [(0, '-- Select Primary Diagnosis --')] + [(d.id, f"{d.name} ({d.code or 'No code'})") for d in diagnoses]

    if form.validate_on_submit():
        record = MedicalRecord(
            clinic_id=get_current_tenant_id(),
            pet_id=pet.id,
            appointment_id=appointment_id,
            doctor_id=current_user.id,
            visit_date=datetime.now(UTC),
            chief_complaint=form.chief_complaint.data,
            examination_notes=form.examination_notes.data,
            temperature=form.temperature.data,
            weight=form.weight.data,
            heart_rate=form.heart_rate.data,
            respiratory_rate=form.respiratory_rate.data,
            blood_pressure=form.blood_pressure.data,
            follow_up_date=form.follow_up_date.data,
            follow_up_notes=form.follow_up_notes.data
        )
        db.session.add(record)
        db.session.flush()

        # Update pet weight if recorded
        if form.weight.data:
            pet.weight = form.weight.data

        # Link diagnosis if chosen
        if form.diagnosis_id.data and form.diagnosis_id.data > 0:
            rec_diag = MedicalRecordDiagnosis(
                medical_record_id=record.id,
                diagnosis_id=form.diagnosis_id.data,
                diagnosis_type='Primary'
            )
            db.session.add(rec_diag)

        # Add initial treatment if provided
        if form.treatment_description.data:
            treatment = Treatment(
                medical_record_id=record.id,
                treatment_type='Clinical Intervention',
                description=form.treatment_description.data,
                status='Active'
            )
            db.session.add(treatment)

        # Mark appointment as completed if linked
        if appointment_id:
            apt = Appointment.query_active().filter_by(id=appointment_id).first()
            if apt:
                apt.status = 'Completed'

        log_activity('CREATE', 'MedicalRecord', record.id, f'Recorded clinical visit for {pet.name}')
        db.session.commit()

        flash(f'Medical examination record created for {pet.name}.', 'success')
        return redirect(url_for('medical.view', id=record.id))

    return render_template('medical/form.html', form=form, pet=pet, appointment_id=appointment_id)


@medical_bp.route('/<int:id>')
@login_required
def view(id):
    record = MedicalRecord.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(record)
    rx_form = PrescriptionItemForm()
    
    # Populate prescription medicines dropdown
    medicines = Medicine.query_active().order_by(Medicine.name).all()
    rx_form.medicine_id.choices = [(m.id, f"{m.name} ({m.strength or m.unit}) - ${m.base_price:.2f}") for m in medicines]

    # Get or create active prescription for this visit
    active_rx = record.prescriptions.filter_by(deleted_at=None).first()

    return render_template(
        'medical/view.html',
        record=record,
        rx_form=rx_form,
        active_rx=active_rx
    )


@medical_bp.route('/<int:id>/prescriptions/add', methods=['POST'])
@login_required
@doctor_required
def add_prescription_item(id):
    record = MedicalRecord.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(record)
    form = PrescriptionItemForm()
    medicines = Medicine.query_active().all()
    form.medicine_id.choices = [(m.id, m.name) for m in medicines]

    if form.validate_on_submit():
        # Find or create prescription container
        prescription = record.prescriptions.filter_by(deleted_at=None).first()
        if not prescription:
            prescription = Prescription(
                medical_record_id=record.id,
                doctor_id=current_user.id,
                status='Active'
            )
            db.session.add(prescription)
            db.session.flush()

        item = PrescriptionItem(
            prescription_id=prescription.id,
            medicine_id=form.medicine_id.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            duration=form.duration.data,
            quantity=form.quantity.data,
            instructions=form.instructions.data
        )
        db.session.add(item)
        log_activity('CREATE', 'PrescriptionItem', item.id, f'Added {item.quantity}x Med ID {item.medicine_id} to Record #{record.id}')
        db.session.commit()
        flash('Medication added to prescription.', 'success')

    return redirect(url_for('medical.view', id=record.id))


@medical_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@doctor_required
def delete(id):
    record = MedicalRecord.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(record)
    record.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'MedicalRecord', record.id, f'Soft-deleted medical record #{record.id}')
    db.session.commit()

    flash(f'Medical record #{record.id} moved to Recycle Bin.', 'warning')
    return redirect(url_for('medical.index'))

