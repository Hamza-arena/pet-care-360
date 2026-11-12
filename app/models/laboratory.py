from datetime import UTC, datetime

from app.extensions import db
from app.models.base import SoftDeleteMixin, TenantMixin, TimestampMixin


class LabTest(SoftDeleteMixin, TimestampMixin, db.Model):
    """Defines available laboratory tests that can be ordered."""
    __tablename__ = 'lab_tests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # Hematology, Biochemistry, Urinalysis, Microbiology, Pathology
    sample_type = db.Column(db.String(50))  # Blood, Urine, Tissue, Swab, Stool
    normal_range = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    base_price = db.Column(db.Float, default=0.0)
    turnaround_hours = db.Column(db.Integer, default=24)

    # Relationships
    order_items = db.relationship('LabOrderItem', backref='lab_test', lazy='dynamic')

    def __repr__(self):
        return f'<LabTest {self.name} ({self.code})>'


class LabOrder(TenantMixin, SoftDeleteMixin, TimestampMixin, db.Model):
    """A laboratory order placed by a doctor for a pet."""
    __tablename__ = 'lab_orders'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    order_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    status = db.Column(db.String(20), default='Pending')  # Pending, Sample-Collected, In-Progress, Completed, Cancelled
    priority = db.Column(db.String(20), default='Routine')  # Routine, Urgent, STAT
    notes = db.Column(db.Text)

    # Relationships
    clinic = db.relationship('Clinic', backref=db.backref('lab_orders', lazy='dynamic'))
    pet = db.relationship('Pet', backref=db.backref('lab_orders', lazy='dynamic'))
    doctor = db.relationship('User', backref=db.backref('lab_orders', lazy='dynamic'))
    items = db.relationship('LabOrderItem', backref='lab_order', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<LabOrder #{self.id} - {self.status}>'


class LabOrderItem(TimestampMixin, db.Model):
    """An individual test item within a lab order."""
    __tablename__ = 'lab_order_items'

    id = db.Column(db.Integer, primary_key=True)
    lab_order_id = db.Column(db.Integer, db.ForeignKey('lab_orders.id'), nullable=False)
    lab_test_id = db.Column(db.Integer, db.ForeignKey('lab_tests.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    notes = db.Column(db.Text)

    # Relationships
    result = db.relationship('LabResult', backref='lab_order_item', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<LabOrderItem #{self.id} - Order #{self.lab_order_id}>'


class LabResult(TimestampMixin, db.Model):
    """The result of a specific lab test order item."""
    __tablename__ = 'lab_results'

    id = db.Column(db.Integer, primary_key=True)
    lab_order_item_id = db.Column(db.Integer, db.ForeignKey('lab_order_items.id'), nullable=False)
    result_value = db.Column(db.String(100))
    result_text = db.Column(db.Text)
    is_abnormal = db.Column(db.Boolean, default=False)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    result_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    # Relationships
    performer = db.relationship('User', foreign_keys=[performed_by],
                                backref=db.backref('performed_lab_results', lazy='dynamic'))
    verifier = db.relationship('User', foreign_keys=[verified_by],
                               backref=db.backref('verified_lab_results', lazy='dynamic'))

    def __repr__(self):
        return f'<LabResult #{self.id} - {"Abnormal" if self.is_abnormal else "Normal"}>'


class Surgery(SoftDeleteMixin, TimestampMixin, db.Model):
    """A surgical procedure scheduled or performed on a pet."""
    __tablename__ = 'surgeries'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    surgery_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Scheduled')  # Scheduled, In-Progress, Completed, Cancelled, Postponed
    anesthesia_type = db.Column(db.String(50))
    complications = db.Column(db.Text)
    post_op_notes = db.Column(db.Text)

    # Relationships
    pet = db.relationship('Pet', backref=db.backref('surgeries', lazy='dynamic'))
    doctor = db.relationship('User', backref=db.backref('surgeries', lazy='dynamic'))
    room = db.relationship('Room', backref=db.backref('surgeries', lazy='dynamic'))

    def __repr__(self):
        return f'<Surgery #{self.id} - {self.surgery_type} ({self.status})>'
