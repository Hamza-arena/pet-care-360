from datetime import UTC, datetime
from decimal import Decimal

from app.extensions import db
from app.models.clinic import Clinic
from app.models.finance import Invoice


def to_decimal(val, default='0.00'):
    """Safely convert any numeric / float / None value to Decimal with 2 decimal places."""
    if val is None or val == '':
        return Decimal(str(default)).quantize(Decimal('0.01'))
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal(str(default)).quantize(Decimal('0.01'))


def generate_next_invoice_number(clinic_id=None):
    """Generate a race-safe, sequential invoice number per clinic (e.g. INV-2026-0001).

    Uses an atomic database-level increment so concurrent requests serialize
    cleanly without duplicate numbers or gaps in both PostgreSQL and SQLite.
    """
    year = datetime.now(UTC).strftime('%Y')

    if clinic_id:
        # Atomic DB-level increment with RETURNING prevents race conditions
        stmt = (
            db.update(Clinic)
            .where(Clinic.id == clinic_id)
            .values(invoice_sequence=db.func.coalesce(Clinic.invoice_sequence, 0) + 1)
            .returning(Clinic.invoice_sequence)
        )
        seq = db.session.execute(stmt).scalar_one()
        db.session.flush()
        return f"INV-{year}-{seq:04d}"

    # Fallback for unassigned clinic / superadmin: lock the most recent invoice
    last_inv = (
        db.session.query(Invoice)
        .filter(Invoice.invoice_number.like(f"INV-{year}-%"))
        .order_by(Invoice.id.desc())
        .with_for_update()
        .first()
    )
    if last_inv and last_inv.invoice_number:
        try:
            parts = last_inv.invoice_number.split('-')
            next_seq = int(parts[-1]) + 1
        except (ValueError, IndexError):
            next_seq = Invoice.query.count() + 1
    else:
        next_seq = 1

    return f"INV-{year}-{next_seq:04d}"


def recalculate_invoice(invoice):
    """Recompute invoice totals with penny-accurate Decimal arithmetic.

    - Subtotal: sum of all line item totals
    - Tax: computed using clinic tax_rate if not manually overridden
    - Discount: deducted from (subtotal + tax)
    - Total: max(0.00, subtotal + tax - discount)
    - Paid: sum of completed payments
    - Status: Paid / Partially-Paid / Unpaid
    """
    # 1. Subtotal = sum of items
    subtotal = sum(
        (to_decimal(item.total_price) for item in invoice.items),
        Decimal('0.00'),
    )
    invoice.subtotal = subtotal.quantize(Decimal('0.01'))

    # 2. Tax: if invoice has a clinic with tax_rate, calculate if tax_amount wasn't explicitly fixed
    tax_rate = Decimal('0.00')
    if invoice.clinic and getattr(invoice.clinic, 'tax_rate', None) is not None:
        tax_rate = to_decimal(invoice.clinic.tax_rate, '0.00')

    # If tax_rate > 0 and no manual tax set, calculate tax
    calc_tax = (invoice.subtotal * (tax_rate / Decimal('100.00'))).quantize(Decimal('0.01'))
    # Use existing non-zero tax_amount if already set, otherwise calculated tax
    existing_tax = to_decimal(invoice.tax_amount, '0.00')
    if existing_tax > Decimal('0.00'):
        invoice.tax_amount = existing_tax
    else:
        invoice.tax_amount = calc_tax

    # 3. Discount
    discount = to_decimal(invoice.discount_amount, '0.00')
    invoice.discount_amount = discount

    # 4. Total = subtotal + tax - discount
    computed_total = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
    invoice.total_amount = max(Decimal('0.00'), computed_total).quantize(Decimal('0.01'))

    # 5. Payments
    paid = sum(
        (
            to_decimal(p.amount)
            for p in invoice.payments
            if not p.is_deleted and p.status == 'Completed'
        ),
        Decimal('0.00'),
    )
    invoice.paid_amount = paid.quantize(Decimal('0.01'))

    # 6. Status
    if invoice.paid_amount >= invoice.total_amount and invoice.total_amount > Decimal('0.00'):
        invoice.status = 'Paid'
    elif invoice.paid_amount > Decimal('0.00'):
        invoice.status = 'Partially-Paid'
    else:
        invoice.status = 'Unpaid'

