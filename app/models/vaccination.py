from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class VaccineCatalog(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'vaccine_catalog'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100))
    description = db.Column(db.Text)
    target_species_id = db.Column(db.Integer, db.ForeignKey('species.id'))
    dose_count = db.Column(db.Integer, default=1)
    interval_days = db.Column(db.Integer)
    validity_months = db.Column(db.Integer)
    side_effects = db.Column(db.Text)

    target_species = db.relationship('Species', backref=db.backref('vaccines', lazy='dynamic'))

    def __repr__(self):
        return f'<VaccineCatalog {self.name}>'


class VaccinationRecord(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'vaccination_records'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    vaccine_id = db.Column(db.Integer, db.ForeignKey('vaccine_catalog.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    administration_date = db.Column(db.Date, nullable=False)
    dose_number = db.Column(db.Integer, default=1)
    batch_number = db.Column(db.String(50))
    next_due_date = db.Column(db.Date)
    site_of_administration = db.Column(db.String(100))
    reaction = db.Column(db.Text)
    notes = db.Column(db.Text)

    pet = db.relationship('Pet', back_populates='vaccination_records')
    vaccine = db.relationship('VaccineCatalog', backref=db.backref('vaccination_records', lazy='dynamic'))
    doctor = db.relationship('User', backref=db.backref('administered_vaccinations', lazy='dynamic'))

    def __repr__(self):
        return f'<VaccinationRecord Pet:{self.pet_id} Vaccine:{self.vaccine_id}>'


class VaccinationReminder(TimestampMixin, db.Model):
    __tablename__ = 'vaccination_reminders'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    vaccine_id = db.Column(db.Integer, db.ForeignKey('vaccine_catalog.id'), nullable=False)
    reminder_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    sent_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    pet = db.relationship('Pet', backref=db.backref('vaccination_reminders', lazy='dynamic'))
    vaccine = db.relationship('VaccineCatalog', backref=db.backref('reminders', lazy='dynamic'))

    def __repr__(self):
        return f'<VaccinationReminder Pet:{self.pet_id} Status:{self.status}>'


class DewormingRecord(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'deworming_records'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    medication_name = db.Column(db.String(100), nullable=False)
    administration_date = db.Column(db.Date, nullable=False)
    dosage = db.Column(db.String(100))
    next_due_date = db.Column(db.Date)
    weight_at_time = db.Column(db.Float)
    notes = db.Column(db.Text)

    pet = db.relationship('Pet', back_populates='deworming_records')
    doctor = db.relationship('User', backref=db.backref('administered_dewormings', lazy='dynamic'))

    def __repr__(self):
        return f'<DewormingRecord Pet:{self.pet_id} Med:{self.medication_name}>'
