from datetime import UTC, datetime

from app.extensions import db
from app.models.base import SoftDeleteMixin, TenantMixin, TimestampMixin


class Invoice(TenantMixin, SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'))
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    due_date = db.Column(db.Date)
    subtotal = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Draft')
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    clinic = db.relationship('Clinic', backref=db.backref('invoices', lazy='dynamic'))
    owner = db.relationship('Owner', backref=db.backref('invoices', lazy='dynamic'))
    pet = db.relationship('Pet', backref=db.backref('invoices', lazy='dynamic'))
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic',
                            cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(TimestampMixin, db.Model):
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    item_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    total_price = db.Column(db.Float, nullable=False)
    reference_type = db.Column(db.String(50))
    reference_id = db.Column(db.Integer)

    def __repr__(self):
        return f'<InvoiceItem {self.description}>'


class Payment(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'))
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    transaction_reference = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Completed')
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)

    method = db.relationship('PaymentMethod', backref=db.backref('payments', lazy='dynamic'))

    def __repr__(self):
        return f'<Payment {self.id} - {self.amount}>'


class PaymentMethod(TimestampMixin, db.Model):
    __tablename__ = 'payment_methods'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<PaymentMethod {self.name}>'
