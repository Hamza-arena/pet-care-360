from datetime import date, datetime

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Medicine(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    generic_name = db.Column(db.String(100))
    category = db.Column(db.String(50))  # Antibiotic, Analgesic, Anti-inflammatory, Vaccine, Supplement, Antiparasitic, Other
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    unit = db.Column(db.String(20))  # Tablet, Capsule, Syrup, Injection, Cream, Drops
    strength = db.Column(db.String(50))
    base_price = db.Column(db.Float, default=0.0)
    requires_prescription = db.Column(db.Boolean, default=True)
    minimum_stock = db.Column(db.Integer, default=10)

    # Relationships
    batches = db.relationship('MedicineBatch', backref='medicine', lazy='dynamic')

    def __repr__(self):
        return f'<Medicine {self.name}>'


class MedicineBatch(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'medicine_batches'

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False)
    quantity_remaining = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    manufacture_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date, nullable=False)
    supplier = db.Column(db.String(100))
    received_date = db.Column(db.Date, default=date.today)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    @property
    def is_expired(self):
        return self.expiry_date < date.today()

    def __repr__(self):
        return f'<MedicineBatch {self.batch_number}>'


class PharmacyDispense(db.Model, TimestampMixin):
    __tablename__ = 'pharmacy_dispenses'

    id = db.Column(db.Integer, primary_key=True)
    prescription_item_id = db.Column(db.Integer, db.ForeignKey('prescription_items.id'))
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'))
    quantity = db.Column(db.Integer, nullable=False)
    dispensed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dispensed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    medicine = db.relationship('Medicine', backref='dispenses')
    batch = db.relationship('MedicineBatch', backref='dispenses')
    dispensed_by_user = db.relationship('User', backref='pharmacy_dispenses', foreign_keys=[dispensed_by])

    def __repr__(self):
        return f'<PharmacyDispense {self.id}>'


class StockMovement(db.Model, TimestampMixin):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'))
    movement_type = db.Column(db.String(20), nullable=False)  # IN, OUT, ADJUSTMENT, RETURN, EXPIRED
    quantity = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(50))  # Purchase, Dispense, Adjustment, Return
    reference_id = db.Column(db.Integer)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    movement_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    medicine = db.relationship('Medicine', backref='stock_movements')
    batch = db.relationship('MedicineBatch', backref='stock_movements')
    performed_by_user = db.relationship('User', backref='stock_movements', foreign_keys=[performed_by])

    def __repr__(self):
        return f'<StockMovement {self.id} {self.movement_type}>'
