from datetime import UTC, datetime
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.finance import InvoiceForm, InvoiceItemForm, PaymentForm
from app.models import (
    Invoice,
    InvoiceItem,
    Owner,
    Payment,
    PaymentMethod,
    Pet,
    log_activity,
)
from app.utils.decorators import staff_required
from app.utils.finance import (
    generate_next_invoice_number,
    recalculate_invoice,
    to_decimal,
)
from app.utils.tenant import assert_tenant_access, get_current_tenant_id, tenant_filter

finance_bp = Blueprint('billing', __name__, url_prefix='/billing')


@finance_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = tenant_filter(Invoice.query_active(), Invoice)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    pagination = query.order_by(Invoice.issue_date.desc()).paginate(page=page, per_page=12, error_out=False)

    total_billed = db.session.query(db.func.sum(Invoice.total_amount)).filter(Invoice.deleted_at.is_(None)).scalar() or 0.0
    total_collected = db.session.query(db.func.sum(Invoice.paid_amount)).filter(Invoice.deleted_at.is_(None)).scalar() or 0.0

    return render_template(
        'billing/index.html',
        pagination=pagination,
        selected_status=status_filter,
        total_billed=total_billed,
        total_collected=total_collected
    )


@finance_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@staff_required
def create_invoice():
    form = InvoiceForm()
    form.owner_id.choices = [(o.id, f"{o.full_name} ({o.phone})") for o in Owner.query_active().all()]
    form.pet_id.choices = [(0, '-- None / General Client Invoice --')] + [(p.id, f"{p.name} ({p.species.name})") for p in Pet.query_active().all()]

    pre_owner = request.args.get('owner_id', type=int)
    if pre_owner and request.method == 'GET':
        form.owner_id.data = pre_owner

    if form.validate_on_submit():
        tenant_id = get_current_tenant_id()
        inv_num = generate_next_invoice_number(tenant_id)

        invoice = Invoice(
            clinic_id=tenant_id,
            invoice_number=inv_num,
            owner_id=form.owner_id.data,
            pet_id=form.pet_id.data if form.pet_id.data and form.pet_id.data > 0 else None,
            due_date=form.due_date.data,
            discount_amount=to_decimal(form.discount_amount.data),
            tax_amount=to_decimal(form.tax_amount.data),
            notes=form.notes.data,
            status='Draft',
            created_by=current_user.id
        )
        db.session.add(invoice)
        db.session.flush()

        recalculate_invoice(invoice)
        log_activity('CREATE', 'Invoice', invoice.id, f'Created invoice {invoice.invoice_number} for Owner ID {invoice.owner_id}')
        db.session.commit()

        flash(f'Invoice {invoice.invoice_number} generated. Add items below.', 'success')
        return redirect(url_for('billing.view_invoice', id=invoice.id))

    return render_template('billing/invoice_form.html', form=form)


@finance_bp.route('/invoices/<int:id>')
@login_required
def view_invoice(id):
    invoice = Invoice.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(invoice)
    item_form = InvoiceItemForm()
    payment_form = PaymentForm()

    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    payment_form.payment_method_id.choices = [(m.id, m.name) for m in payment_methods]
    payment_form.amount.data = max(0.0, invoice.balance_due)

    return render_template(
        'billing/view_invoice.html',
        invoice=invoice,
        item_form=item_form,
        payment_form=payment_form
    )


@finance_bp.route('/invoices/<int:id>/items/add', methods=['POST'])
@login_required
@staff_required
def add_item(id):
    invoice = Invoice.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(invoice)
    form = InvoiceItemForm()
    if form.validate_on_submit():
        qty = form.quantity.data
        price = to_decimal(form.unit_price.data)
        total = (Decimal(qty) * price).quantize(Decimal('0.01'))

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=form.description.data.strip(),
            item_type=form.item_type.data,
            quantity=qty,
            unit_price=price,
            total_price=total
        )
        db.session.add(item)
        recalculate_invoice(invoice)
        currency = invoice.clinic.currency if invoice.clinic and getattr(invoice.clinic, 'currency', None) else 'PKR'
        log_activity('UPDATE', 'Invoice', invoice.id, f'Added item "{item.description}" ({currency} {total:.2f})')
        db.session.commit()
        flash(f'Added line item: {item.description}', 'success')

    return redirect(url_for('billing.view_invoice', id=invoice.id))


@finance_bp.route('/invoices/<int:id>/payments/new', methods=['POST'])
@login_required
@staff_required
def add_payment(id):
    invoice = Invoice.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(invoice)
    form = PaymentForm()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    form.payment_method_id.choices = [(m.id, m.name) for m in payment_methods]

    if form.validate_on_submit():
        pay_amount = to_decimal(form.amount.data)
        payment = Payment(
            invoice_id=invoice.id,
            payment_method_id=form.payment_method_id.data,
            amount=pay_amount,
            transaction_reference=form.transaction_reference.data,
            notes=form.notes.data,
            status='Completed',
            received_by=current_user.id,
            payment_date=datetime.now(UTC)
        )
        db.session.add(payment)
        db.session.flush()

        recalculate_invoice(invoice)
        currency = invoice.clinic.currency if invoice.clinic and getattr(invoice.clinic, 'currency', None) else 'PKR'
        log_activity('CREATE', 'Payment', payment.id, f'Recorded payment of {currency} {pay_amount:.2f} for Invoice #{invoice.invoice_number}')
        db.session.commit()

        flash(f'Payment of {currency} {pay_amount:.2f} recorded successfully!', 'success')

    return redirect(url_for('billing.view_invoice', id=invoice.id))


@finance_bp.route('/invoices/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_invoice(id):
    invoice = Invoice.query_active().filter_by(id=id).first_or_404()
    assert_tenant_access(invoice)
    invoice.soft_delete(user_id=current_user.id)
    log_activity('DELETE', 'Invoice', invoice.id, f'Soft-deleted invoice {invoice.invoice_number}')
    db.session.commit()

    flash(f'Invoice {invoice.invoice_number} moved to Recycle Bin.', 'warning')
    return redirect(url_for('billing.index'))

