try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from app.extensions import db
from app.models.base import SoftDeleteMixin, TenantMixin, TimestampMixin


class MedicalRecord(TenantMixin, SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'medical_records'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    chief_complaint = db.Column(db.Text)
    examination_notes = db.Column(db.Text)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)
    blood_pressure = db.Column(db.String(20))
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)

    # Relationships
    clinic = db.relationship('Clinic', backref=db.backref('medical_records', lazy='dynamic'))
    pet = db.relationship('Pet', back_populates='medical_records')
    doctor = db.relationship('User', backref=db.backref('medical_records', lazy='dynamic'))
    appointment = db.relationship('Appointment', back_populates='medical_records')
    diagnoses = db.relationship('MedicalRecordDiagnosis', backref='medical_record', lazy='dynamic',
                                cascade='all, delete-orphan')
    treatments = db.relationship('Treatment', backref='medical_record', lazy='dynamic',
                                 cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', backref='medical_record', lazy='dynamic',
                                    cascade='all, delete-orphan')

    def __repr__(self):
        return f'<MedicalRecord {self.id} - Pet {self.pet_id}>'


class Diagnosis(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'diagnoses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))

    def __repr__(self):
        return f'<Diagnosis {self.code} - {self.name}>'


class MedicalRecordDiagnosis(db.Model):
    __tablename__ = 'medical_record_diagnoses'
    __table_args__ = (
        db.UniqueConstraint('medical_record_id', 'diagnosis_id', name='uq_record_diagnosis'),
    )

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'), nullable=False)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id'), nullable=False)
    diagnosis_type = db.Column(db.String(20), default='Primary')
    notes = db.Column(db.Text)

    # Relationships
    diagnosis = db.relationship('Diagnosis', backref=db.backref('medical_record_diagnoses', lazy='dynamic'))

    def __repr__(self):
        return f'<MedicalRecordDiagnosis Record:{self.medical_record_id} Diagnosis:{self.diagnosis_id}>'


class Treatment(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'treatments'

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'), nullable=False)
    treatment_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Active')
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Treatment {self.id} - {self.treatment_type}>'


class Prescription(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prescription_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    status = db.Column(db.String(20), default='Active')
    notes = db.Column(db.Text)

    # Relationships
    items = db.relationship('PrescriptionItem', backref='prescription', lazy='dynamic',
                            cascade='all, delete-orphan')
    doctor = db.relationship('User', backref=db.backref('prescriptions', lazy='dynamic'))

    def __repr__(self):
        return f'<Prescription {self.id} - Record {self.medical_record_id}>'


class PrescriptionItem(TimestampMixin, db.Model):
    __tablename__ = 'prescription_items'

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False)
    instructions = db.Column(db.Text)

    # Relationships
    medicine = db.relationship('Medicine', backref=db.backref('prescription_items', lazy='dynamic'))

    def __repr__(self):
        return f'<PrescriptionItem {self.id} - Prescription {self.prescription_id}>'
