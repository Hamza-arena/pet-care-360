from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.pets import AllergyForm, PetForm
from app.models import (
    Allergy,
    Breed,
    LabOrder,
    MedicalRecord,
    Owner,
    Pet,
    Species,
    VaccinationRecord,
    log_activity,
)
from app.utils.decorators import staff_required
from app.utils.tenant import assert_tenant_access, tenant_filter

pets_bp = Blueprint('pets', __name__, url_prefix='/pets')


@pets_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()
    species_id = request.args.get('species_id', type=int)

    query = tenant_filter(Pet.query_active(), Pet)
    if search_q:
        search_filter = f"%{search_q}%"
        query = query.filter(
            (Pet.name.ilike(search_filter)) |
            (Pet.microchip_number.ilike(search_filter)) |
            (Pet.color.ilike(search_filter))
        )
    if species_id:
        query = query.filter(Pet.species_id == species_id)

    pagination = query.order_by(Pet.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    species_list = Species.query_active().all()

    return render_template(
        'pets/index.html',
        pagination=pagination,
        search_q=search_q,
        species_list=species_list,
        selected_species=species_id
    )


@pets_bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    form = PetForm()
    # Populate dynamic select fields
    form.owner_id.choices = [(o.id, f"{o.full_name} ({o.phone})") for o in Owner.query_active().order_by(Owner.first_name).all()]
    form.species_id.choices = [(s.id, s.name) for s in Species.query_active().order_by(Species.name).all()]
    
    # Pre-select owner if passed via query string
    pre_owner = request.args.get('owner_id', type=int)
    if pre_owner and request.method == 'GET':
        form.owner_id.data = pre_owner

    selected_species_id = form.species_id.data or (form.species_id.choices[0][0] if form.species_id.choices else None)
    if selected_species_id:
        form.breed_id.choices = [(0, 'Mixed / Unknown Breed')] + [(b.id, b.name) for b in Breed.query_active().filter_by(species_id=selected_species_id).all()]
    else:
        form.breed_id.choices = [(0, 'Mixed / Unknown Breed')]

    if form.validate_on_submit():
        breed_val = form.breed_id.data if form.breed_id.data and form.breed_id.data > 0 else None
        pet = Pet(
            name=form.name.data.strip(),
            owner_id=form.owner_id.data,
            species_id=form.species_id.data,
            breed_id=breed_val,
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            color=form.color.data.strip() if form.color.data else None,
            weight=form.weight.data,
            microchip_number=form.microchip_number.data.strip() if form.microchip_number.data else None,
            is_neutered=form.is_neutered.data,
            insurance_number=form.insurance_number.data.strip() if form.insurance_number.data else None,
            notes=form.notes.data
        )
        db.session.add(pet)
        db.session.flush()

        log_activity('CREATE', 'Pet', pet.id, f'Registered pet {pet.name} for Owner ID {pet.owner_id}')
        db.session.commit()

        flash(f'Pet "{pet.name}" has been successfully added to the system!', 'success')
        return redirect(url_for('pets.view', id=pet.id))

    return render_template('pets/form.html', form=form, title='Add New Pet')


@pets_bp.route('/<int:id>')
@login_required
def view(id):
    pet = Pet.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(pet)
    allergy_form = AllergyForm()

    medical_records = MedicalRecord.query_active().filter_by(pet_id=pet.id).order_by(MedicalRecord.visit_date.desc()).all()
    vaccinations = VaccinationRecord.query_active().filter_by(pet_id=pet.id).order_by(VaccinationRecord.administration_date.desc()).all()
    dewormings = [d for d in pet.deworming_records if not d.is_deleted]
    lab_orders = LabOrder.query_active().filter_by(pet_id=pet.id).order_by(LabOrder.order_date.desc()).all()
    appointments = [a for a in pet.appointments if not a.is_deleted]
    allergies = [a for a in pet.allergies if not a.is_deleted]

    return render_template(
        'pets/view.html',
        pet=pet,
        allergy_form=allergy_form,
        medical_records=medical_records,
        vaccinations=vaccinations,
        dewormings=dewormings,
        lab_orders=lab_orders,
        appointments=appointments,
        allergies=allergies
    )


@pets_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit(id):
    pet = Pet.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(pet)
    form = PetForm(obj=pet)

    form.owner_id.choices = [(o.id, f"{o.full_name} ({o.phone})") for o in Owner.query_active().order_by(Owner.first_name).all()]
    form.species_id.choices = [(s.id, s.name) for s in Species.query_active().order_by(Species.name).all()]
    
    current_species = form.species_id.data or pet.species_id
    form.breed_id.choices = [(0, 'Mixed / Unknown Breed')] + [(b.id, b.name) for b in Breed.query_active().filter_by(species_id=current_species).all()]

    if request.method == 'GET':
        form.breed_id.data = pet.breed_id or 0

    if form.validate_on_submit():
        pet.name = form.name.data.strip()
        pet.owner_id = form.owner_id.data
        pet.species_id = form.species_id.data
        pet.breed_id = form.breed_id.data if form.breed_id.data and form.breed_id.data > 0 else None
        pet.gender = form.gender.data
        pet.date_of_birth = form.date_of_birth.data
        pet.color = form.color.data.strip() if form.color.data else None
        pet.weight = form.weight.data
        pet.microchip_number = form.microchip_number.data.strip() if form.microchip_number.data else None
        pet.is_neutered = form.is_neutered.data
        pet.insurance_number = form.insurance_number.data.strip() if form.insurance_number.data else None
        pet.notes = form.notes.data

        log_activity('UPDATE', 'Pet', pet.id, f'Updated pet profile: {pet.name}')
        db.session.commit()
        flash(f'Pet "{pet.name}" details updated successfully.', 'success')
        return redirect(url_for('pets.view', id=pet.id))

    return render_template('pets/form.html', form=form, title=f'Edit Pet: {pet.name}', pet=pet)


@pets_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete(id):
    pet = Pet.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(pet)
    pet.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'Pet', pet.id, f'Soft-deleted pet {pet.name}')
    db.session.commit()

    flash(f'Pet "{pet.name}" moved to Recycle Bin. You can restore it anytime.', 'warning')
    return redirect(url_for('pets.index'))


@pets_bp.route('/<int:id>/allergies/add', methods=['POST'])
@login_required
@staff_required
def add_allergy(id):
    pet = Pet.query_active().filter_by(id=id).first_or_404()
    form = AllergyForm()
    if form.validate_on_submit():
        allergy = Allergy(
            pet_id=pet.id,
            allergen=form.allergen.data.strip(),
            severity=form.severity.data,
            reaction=form.reaction.data,
            diagnosed_date=form.diagnosed_date.data,
            notes=form.notes.data
        )
        db.session.add(allergy)
        log_activity('CREATE', 'Allergy', pet.id, f'Added allergy {allergy.allergen} to pet {pet.name}')
        db.session.commit()
        flash(f'Allergy "{allergy.allergen}" recorded for {pet.name}.', 'success')
    return redirect(url_for('pets.view', id=pet.id))


@pets_bp.route('/api/breeds/<int:species_id>')
@login_required
def get_breeds_by_species(species_id):
    breeds = Breed.query_active().filter_by(species_id=species_id).order_by(Breed.name).all()
    return jsonify([{'id': b.id, 'name': b.name} for b in breeds])

