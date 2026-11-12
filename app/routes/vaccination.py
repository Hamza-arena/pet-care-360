from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.forms.vaccination import DewormingRecordForm, VaccinationRecordForm
from app.models import (
    DewormingRecord,
    Pet,
    User,
    VaccinationRecord,
    VaccinationReminder,
    VaccineCatalog,
    log_activity,
)
from app.utils.decorators import doctor_required

vaccination_bp = Blueprint('vaccination', __name__, url_prefix='/vaccination')


@vaccination_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'vaccines')
    page = request.args.get('page', 1, type=int)

    if tab == 'deworming':
        pagination = DewormingRecord.query_active().order_by(DewormingRecord.administration_date.desc()).paginate(page=page, per_page=15, error_out=False)
    elif tab == 'reminders':
        pagination = VaccinationReminder.query.order_by(VaccinationReminder.reminder_date.asc()).paginate(page=page, per_page=15, error_out=False)
    else:
        pagination = VaccinationRecord.query_active().order_by(VaccinationRecord.administration_date.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('vaccination/index.html', pagination=pagination, current_tab=tab)


@vaccination_bp.route('/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def create():
    form = VaccinationRecordForm()
    form.pet_id.choices = [(p.id, f"{p.name} ({p.species.name} - Owner: {p.owner.full_name})") for p in Pet.query_active().all()]
    form.vaccine_id.choices = [(v.id, f"{v.name} ({v.manufacturer or 'General'})") for v in VaccineCatalog.query_active().all()]
    doctors = [u for u in User.query_active().all() if u.has_role('Doctor') or u.has_role('Admin')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name}") for d in doctors]

    pre_pet = request.args.get('pet_id', type=int)
    if pre_pet and request.method == 'GET':
        form.pet_id.data = pre_pet
        form.administration_date.data = date.today()

    if form.validate_on_submit():
        record = VaccinationRecord(
            pet_id=form.pet_id.data,
            vaccine_id=form.vaccine_id.data,
            doctor_id=form.doctor_id.data,
            administration_date=form.administration_date.data,
            dose_number=form.dose_number.data,
            batch_number=form.batch_number.data,
            next_due_date=form.next_due_date.data,
            site_of_administration=form.site_of_administration.data,
            reaction=form.reaction.data,
            notes=form.notes.data
        )
        db.session.add(record)
        db.session.flush()

        # If next due date is provided, create automated reminder
        if record.next_due_date:
            reminder = VaccinationReminder(
                pet_id=record.pet_id,
                vaccine_id=record.vaccine_id,
                reminder_date=record.next_due_date,
                status='Pending',
                notes=f'Dose #{record.dose_number + 1} booster reminder'
            )
            db.session.add(reminder)

        log_activity('CREATE', 'VaccinationRecord', record.id, f'Administered vaccine ID {record.vaccine_id} to Pet ID {record.pet_id}')
        db.session.commit()

        flash('Vaccination record created and booster reminder scheduled.', 'success')
        return redirect(url_for('pets.view', id=record.pet_id))

    return render_template('vaccination/form.html', form=form, title='Administer Vaccination')


@vaccination_bp.route('/deworming/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_deworming():
    form = DewormingRecordForm()
    form.pet_id.choices = [(p.id, f"{p.name} ({p.species.name} - Owner: {p.owner.full_name})") for p in Pet.query_active().all()]
    doctors = [u for u in User.query_active().all() if u.has_role('Doctor') or u.has_role('Admin')]
    form.doctor_id.choices = [(0, '-- None / Assistant --')] + [(d.id, f"Dr. {d.first_name} {d.last_name}") for d in doctors]

    pre_pet = request.args.get('pet_id', type=int)
    if pre_pet and request.method == 'GET':
        form.pet_id.data = pre_pet
        form.administration_date.data = date.today()

    if form.validate_on_submit():
        doc_id = form.doctor_id.data if form.doctor_id.data and form.doctor_id.data > 0 else None
        record = DewormingRecord(
            pet_id=form.pet_id.data,
            doctor_id=doc_id,
            medication_name=form.medication_name.data.strip(),
            administration_date=form.administration_date.data,
            dosage=form.dosage.data,
            next_due_date=form.next_due_date.data,
            notes=form.notes.data
        )
        db.session.add(record)
        log_activity('CREATE', 'DewormingRecord', record.id, f'Dewormed Pet ID {record.pet_id} with {record.medication_name}')
        db.session.commit()

        flash('Deworming record saved successfully.', 'success')
        return redirect(url_for('pets.view', id=record.pet_id))

    return render_template('vaccination/deworming_form.html', form=form)

