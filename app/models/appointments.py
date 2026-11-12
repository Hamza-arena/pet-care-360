from datetime import datetime, timezone

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class AppointmentType(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'appointment_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=30)
    base_fee = db.Column(db.Float, default=0.0)

    appointments = db.relationship('Appointment', back_populates='appointment_type', lazy='dynamic')

    def __repr__(self):
        return f'<AppointmentType {self.name}>'


class Appointment(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_types.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Scheduled')
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    pet = db.relationship('Pet', backref=db.backref('appointments', lazy='dynamic'))
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref=db.backref('doctor_appointments', lazy='dynamic'))
    clinic = db.relationship('Clinic', backref=db.backref('appointments', lazy='dynamic'))
    appointment_type = db.relationship('AppointmentType', back_populates='appointments')
    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('created_appointments', lazy='dynamic'))
    status_history = db.relationship('AppointmentStatusHistory', back_populates='appointment', lazy='dynamic', order_by='AppointmentStatusHistory.changed_at.desc()')
    medical_records = db.relationship('MedicalRecord', back_populates='appointment', lazy='dynamic')
    queue_token = db.relationship('QueueToken', back_populates='appointment', uselist=False)

    def __repr__(self):
        return f'<Appointment {self.id} - {self.status}>'


class AppointmentStatusHistory(db.Model):
    __tablename__ = 'appointment_status_history'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text)

    appointment = db.relationship('Appointment', back_populates='status_history')
    user = db.relationship('User', backref=db.backref('status_changes', lazy='dynamic'))

    def __repr__(self):
        return f'<AppointmentStatusHistory {self.old_status} -> {self.new_status}>'


class QueueToken(db.Model, TimestampMixin):
    __tablename__ = 'queue_tokens'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    token_number = db.Column(db.String(10), nullable=False)
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    called_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Waiting')
    counter_number = db.Column(db.String(10))

    appointment = db.relationship('Appointment', back_populates='queue_token')

    def __repr__(self):
        return f'<QueueToken {self.token_number} - {self.status}>'
