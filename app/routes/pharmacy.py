import csv
import io
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.pharmacy import DispenseForm, MedicineBatchForm, MedicineForm
from app.models import (
    Medicine,
    MedicineBatch,
    PharmacyDispense,
    StockMovement,
    log_activity,
)
from app.utils.decorators import staff_required
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

pharmacy_bp = Blueprint('pharmacy', __name__, url_prefix='/pharmacy')


@pharmacy_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '')

    query = tenant_filter(Medicine.query_active(), Medicine)
    if search_q:
        search_filter = f"%{search_q}%"
        query = query.filter(
            (Medicine.name.ilike(search_filter)) |
            (Medicine.generic_name.ilike(search_filter)) |
            (Medicine.manufacturer.ilike(search_filter))
        )
    if category_filter:
        query = query.filter(Medicine.category == category_filter)

    pagination = query.order_by(Medicine.name.asc()).paginate(page=page, per_page=12, error_out=False)

    # Compute stock summary for current items
    med_stock_info = []
    for m in pagination.items:
        total_remaining = sum(b.quantity_remaining for b in m.batches if not b.is_deleted)
        batches_active = [b for b in m.batches if not b.is_deleted and b.quantity_remaining > 0]
        is_low = total_remaining <= m.minimum_stock
        med_stock_info.append({
            'medicine': m,
            'total_stock': total_remaining,
            'batch_count': len(batches_active),
            'is_low': is_low
        })

    categories = [
        'Antibiotic', 'Analgesic', 'Anti-inflammatory', 'Vaccine',
        'Supplement', 'Antiparasitic', 'Dermatological', 'Other'
    ]

    return render_template(
        'pharmacy/index.html',
        pagination=pagination,
        med_stock_info=med_stock_info,
        search_q=search_q,
        categories=categories,
        selected_category=category_filter
    )


@pharmacy_bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    form = MedicineForm()
    if form.validate_on_submit():
        med = Medicine(
            clinic_id=get_current_tenant_id(),
            name=form.name.data.strip(),
            generic_name=form.generic_name.data.strip() if form.generic_name.data else None,
            category=form.category.data,
            description=form.description.data,
            manufacturer=form.manufacturer.data.strip() if form.manufacturer.data else None,
            unit=form.unit.data,
            strength=form.strength.data.strip() if form.strength.data else None,
            base_price=form.base_price.data,
            requires_prescription=form.requires_prescription.data,
            minimum_stock=form.minimum_stock.data
        )
        db.session.add(med)
        db.session.flush()

        log_activity('CREATE', 'Medicine', med.id, f'Added medicine {med.name} ({med.strength or med.unit})')
        db.session.commit()
        flash(f'Medicine "{med.name}" cataloged successfully.', 'success')
        return redirect(url_for('pharmacy.view', id=med.id))

    return render_template('pharmacy/form.html', form=form, title='Add New Medication to Catalog')


@pharmacy_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit(id):
    medicine = Medicine.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(medicine)
    form = MedicineForm(obj=medicine)

    if form.validate_on_submit():
        medicine.name = form.name.data.strip()
        medicine.generic_name = form.generic_name.data.strip() if form.generic_name.data else None
        medicine.category = form.category.data
        medicine.description = form.description.data
        medicine.manufacturer = form.manufacturer.data.strip() if form.manufacturer.data else None
        medicine.unit = form.unit.data
        medicine.strength = form.strength.data.strip() if form.strength.data else None
        medicine.base_price = form.base_price.data
        medicine.requires_prescription = form.requires_prescription.data
        medicine.minimum_stock = form.minimum_stock.data

        log_activity('UPDATE', 'Medicine', medicine.id, f'Updated medicine {medicine.name}')
        db.session.commit()
        flash(f'Medicine "{medicine.name}" updated successfully.', 'success')
        return redirect(url_for('pharmacy.view', id=medicine.id))

    return render_template('pharmacy/form.html', form=form, title=f'Edit Medicine: {medicine.name}', medicine=medicine)


@pharmacy_bp.route('/<int:id>')
@login_required
def view(id):
    medicine = Medicine.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(medicine)
    active_batches = [b for b in medicine.batches if not b.is_deleted]
    total_qty = sum(b.quantity_remaining for b in active_batches)

    dispense_form = DispenseForm()
    available_batches = [b for b in active_batches if b.quantity_remaining > 0]
    dispense_form.batch_id.choices = [(b.id, f"Lot #{b.batch_number} (Exp: {b.expiry_date}) - {b.quantity_remaining} left") for b in available_batches]

    batch_form = MedicineBatchForm()

    return render_template(
        'pharmacy/view.html',
        medicine=medicine,
        active_batches=active_batches,
        total_qty=total_qty,
        dispense_form=dispense_form,
        batch_form=batch_form
    )


@pharmacy_bp.route('/<int:id>/batches/new', methods=['POST'])
@login_required
@staff_required
def add_batch(id):
    medicine = Medicine.query_active().filter_by(id=id).first_or_404()
    form = MedicineBatchForm()
    if form.validate_on_submit():
        batch = MedicineBatch(
            medicine_id=medicine.id,
            batch_number=form.batch_number.data.strip(),
            quantity_received=form.quantity_received.data,
            quantity_remaining=form.quantity_received.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data or medicine.base_price,
            manufacture_date=form.manufacture_date.data,
            expiry_date=form.expiry_date.data,
            supplier=form.supplier.data,
            received_by=current_user.id
        )
        db.session.add(batch)
        db.session.flush()

        # Record stock movement IN
        movement = StockMovement(
            medicine_id=medicine.id,
            batch_id=batch.id,
            movement_type='IN',
            quantity=batch.quantity_received,
            reference_type='Purchase / Delivery',
            reference_id=batch.id,
            performed_by=current_user.id,
            notes=f'Received Lot #{batch.batch_number} from {batch.supplier or "Supplier"}'
        )
        db.session.add(movement)
        log_activity('CREATE', 'MedicineBatch', batch.id, f'Received batch {batch.batch_number} ({batch.quantity_received} units)')
        db.session.commit()

        flash(f'Batch #{batch.batch_number} ({batch.quantity_received} units) added to inventory.', 'success')

    return redirect(url_for('pharmacy.view', id=medicine.id))


@pharmacy_bp.route('/<int:id>/dispense', methods=['POST'])
@login_required
@staff_required
def dispense(id):
    medicine = Medicine.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(medicine)
    form = DispenseForm()
    available_batches = [b for b in medicine.batches if not b.is_deleted and b.quantity_remaining > 0]
    form.batch_id.choices = [(0, '-- Auto FEFO (First-Expired, First-Out) --')] + [
        (b.id, f"{b.batch_number} (Exp: {b.expiry_date}, Rem: {b.quantity_remaining})")
        for b in available_batches
    ]

    if form.validate_on_submit():
        dispense_qty = form.quantity.data
        if dispense_qty <= 0:
            abort(400, description="Dispense quantity must be greater than zero.")

        # Specific batch requested
        if form.batch_id.data and form.batch_id.data > 0:
            batch = MedicineBatch.query_active().filter_by(id=form.batch_id.data).first_or_404()
            if batch.is_expired:
                abort(400, description=f"Cannot dispense from expired batch #{batch.batch_number} (expired on {batch.expiry_date}).")

            if dispense_qty > batch.quantity_remaining:
                abort(400, description=f"Cannot dispense {dispense_qty} units! Only {batch.quantity_remaining} available in batch #{batch.batch_number}.")

            batch.quantity_remaining -= dispense_qty

            dispense_rec = PharmacyDispense(
                medicine_id=medicine.id,
                batch_id=batch.id,
                quantity=dispense_qty,
                dispensed_by=current_user.id,
                dispensed_at=datetime.now(UTC),
                notes=form.notes.data
            )
            db.session.add(dispense_rec)

            movement = StockMovement(
                medicine_id=medicine.id,
                batch_id=batch.id,
                movement_type='OUT',
                quantity=dispense_qty,
                reference_type='Dispense',
                reference_id=dispense_rec.id,
                performed_by=current_user.id,
                notes=form.notes.data or 'Dispensed to patient'
            )
            db.session.add(movement)
            log_activity('UPDATE', 'StockMovement', movement.id, f'Dispensed {dispense_qty}x {medicine.name} from Batch #{batch.batch_number}')
        else:
            # Auto-FEFO (First-Expired, First-Out)
            fefo_batches = [
                b for b in medicine.batches
                if not b.is_deleted and not b.is_expired and b.quantity_remaining > 0
            ]
            fefo_batches.sort(key=lambda b: b.expiry_date)
            total_available = sum(b.quantity_remaining for b in fefo_batches)
            if dispense_qty > total_available:
                abort(400, description=f"Cannot dispense {dispense_qty} units! Only {total_available} non-expired units available.")

            remaining_to_dispense = dispense_qty
            for batch in fefo_batches:
                if remaining_to_dispense <= 0:
                    break
                take = min(batch.quantity_remaining, remaining_to_dispense)
                batch.quantity_remaining -= take
                remaining_to_dispense -= take

                dispense_rec = PharmacyDispense(
                    medicine_id=medicine.id,
                    batch_id=batch.id,
                    quantity=take,
                    dispensed_by=current_user.id,
                    dispensed_at=datetime.now(UTC),
                    notes=form.notes.data
                )
                db.session.add(dispense_rec)

                movement = StockMovement(
                    medicine_id=medicine.id,
                    batch_id=batch.id,
                    movement_type='OUT',
                    quantity=take,
                    reference_type='Dispense',
                    reference_id=dispense_rec.id,
                    performed_by=current_user.id,
                    notes=form.notes.data or 'Dispensed to patient (FEFO)'
                )
                db.session.add(movement)
                log_activity('UPDATE', 'StockMovement', movement.id, f'FEFO dispensed {take}x {medicine.name} from Batch #{batch.batch_number}')

        db.session.commit()
        flash(f'Successfully dispensed {dispense_qty} units of {medicine.name}. Stock updated.', 'success')

    return redirect(url_for('pharmacy.view', id=medicine.id))


@pharmacy_bp.route('/export/csv')
@login_required
@staff_required
def export_csv():
    query = tenant_filter(Medicine.query_active(), Medicine)
    medicines = query.order_by(Medicine.name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Medicine Name',
        'Generic Name',
        'Category',
        'Unit',
        'Strength',
        'Base Price',
        'Current Stock',
        'Minimum Stock',
        'Stock Status',
    ])

    for med in medicines:
        total_remaining = sum(b.quantity_remaining for b in med.batches if not b.is_deleted)
        if total_remaining == 0:
            status = 'Out of Stock'
        elif total_remaining <= med.minimum_stock:
            status = 'Low Stock'
        else:
            status = 'In Stock'

        writer.writerow([
            med.name,
            med.generic_name or '',
            med.category or '',
            med.unit or '',
            med.strength or '',
            f"{med.base_price:.2f}",
            total_remaining,
            med.minimum_stock,
            status,
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=pharmacy_inventory_report.csv'},
    )


@pharmacy_bp.route('/movements')
@login_required
def movements():
    page = request.args.get('page', 1, type=int)
    pagination = StockMovement.query.order_by(StockMovement.movement_date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('pharmacy/movements.html', pagination=pagination)


@pharmacy_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete(id):
    medicine = Medicine.query_active().filter_by(id=id).first_or_404()
    medicine.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'Medicine', medicine.id, f'Soft-deleted medicine {medicine.name}')
    db.session.commit()

    flash(f'Medicine "{medicine.name}" moved to Recycle Bin.', 'warning')
    return redirect(url_for('pharmacy.index'))

