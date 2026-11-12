from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.owners import OwnerForm
from app.models import Owner, OwnerAddress, log_activity
from app.utils.decorators import staff_required
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

owners_bp = Blueprint('owners', __name__, url_prefix='/owners')


@owners_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()

    query = tenant_filter(Owner.query_active(), Owner)
    if search_q:
        search_filter = f"%{search_q}%"
        query = query.filter(
            (Owner.first_name.ilike(search_filter)) |
            (Owner.last_name.ilike(search_filter)) |
            (Owner.phone.ilike(search_filter)) |
            (Owner.email.ilike(search_filter))
        )

    pagination = query.order_by(Owner.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('owners/index.html', pagination=pagination, search_q=search_q)


@owners_bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    form = OwnerForm()
    if form.validate_on_submit():
        owner = Owner(
            clinic_id=get_current_tenant_id(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.strip().lower() if form.email.data else None,
            phone=form.phone.data.strip(),
            emergency_contact=form.emergency_contact.data.strip() if form.emergency_contact.data else None,
            date_of_birth=form.date_of_birth.data,
            national_id=form.national_id.data.strip() if form.national_id.data else None,
            notes=form.notes.data,
            registered_by=current_user.id
        )
        db.session.add(owner)
        db.session.flush()

        # Add primary address if provided
        if form.street_address.data or form.city.data:
            address = OwnerAddress(
                owner_id=owner.id,
                street_address=form.street_address.data or 'N/A',
                city=form.city.data or 'N/A',
                state=form.state.data,
                postal_code=form.postal_code.data,
                is_primary=True
            )
            db.session.add(address)

        log_activity('CREATE', 'Owner', owner.id, f'Registered owner {owner.full_name}')
        db.session.commit()
        flash(f'Owner {owner.full_name} registered successfully!', 'success')
        return redirect(url_for('owners.view', id=owner.id))

    return render_template('owners/form.html', form=form, title='Register New Pet Owner')


@owners_bp.route('/<int:id>')
@login_required
def view(id):
    owner = Owner.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(owner)
    active_pets = [p for p in owner.pets if not p.is_deleted]
    active_invoices = [inv for inv in owner.invoices if not inv.is_deleted]
    return render_template('owners/view.html', owner=owner, pets=active_pets, invoices=active_invoices)


@owners_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit(id):
    owner = Owner.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(owner)
    form = OwnerForm(obj=owner)

    primary_addr = next((a for a in owner.addresses if a.is_primary and not a.is_deleted), None)

    if request.method == 'GET' and primary_addr:
        form.street_address.data = primary_addr.street_address
        form.city.data = primary_addr.city
        form.state.data = primary_addr.state
        form.postal_code.data = primary_addr.postal_code

    if form.validate_on_submit():
        owner.first_name = form.first_name.data.strip()
        owner.last_name = form.last_name.data.strip()
        owner.email = form.email.data.strip().lower() if form.email.data else None
        owner.phone = form.phone.data.strip()
        owner.emergency_contact = form.emergency_contact.data.strip() if form.emergency_contact.data else None
        owner.date_of_birth = form.date_of_birth.data
        owner.national_id = form.national_id.data.strip() if form.national_id.data else None
        owner.notes = form.notes.data

        if form.street_address.data or form.city.data:
            if primary_addr:
                primary_addr.street_address = form.street_address.data or 'N/A'
                primary_addr.city = form.city.data or 'N/A'
                primary_addr.state = form.state.data
                primary_addr.postal_code = form.postal_code.data
            else:
                new_addr = OwnerAddress(
                    owner_id=owner.id,
                    street_address=form.street_address.data or 'N/A',
                    city=form.city.data or 'N/A',
                    state=form.state.data,
                    postal_code=form.postal_code.data,
                    is_primary=True
                )
                db.session.add(new_addr)

        log_activity('UPDATE', 'Owner', owner.id, f'Updated owner {owner.full_name}')
        db.session.commit()
        flash(f'Owner {owner.full_name} details updated.', 'success')
        return redirect(url_for('owners.view', id=owner.id))

    return render_template('owners/form.html', form=form, title=f'Edit Owner: {owner.full_name}', owner=owner)


@owners_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete(id):
    owner = Owner.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(owner)
    owner.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'Owner', owner.id, f'Soft-deleted owner {owner.full_name}')
    db.session.commit()

    flash(f'Owner "{owner.full_name}" moved to Recycle Bin. You can restore them anytime from the Admin panel.', 'warning')
    return redirect(url_for('owners.index'))

