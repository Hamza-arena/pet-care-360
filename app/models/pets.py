from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Species(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'species'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

    breeds = db.relationship('Breed', back_populates='species', lazy='dynamic')
    pets = db.relationship('Pet', back_populates='species', lazy='dynamic')

    def __repr__(self):
        return f'<Species {self.name}>'


class Breed(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'breeds'

    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    average_lifespan = db.Column(db.String(20))
    average_weight = db.Column(db.String(20))

    species = db.relationship('Species', back_populates='breeds')
    pets = db.relationship('Pet', back_populates='breed', lazy='dynamic')

    def __repr__(self):
        return f'<Breed {self.name}>'


class Pet(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'pets'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), nullable=False)
    breed_id = db.Column(db.Integer, db.ForeignKey('breeds.id'))
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10))  # Male, Female, Unknown
    date_of_birth = db.Column(db.Date)
    color = db.Column(db.String(50))
    weight = db.Column(db.Float)
    microchip_number = db.Column(db.String(50), unique=True)
    is_neutered = db.Column(db.Boolean, default=False)
    insurance_number = db.Column(db.String(50))
    notes = db.Column(db.Text)

    owner = db.relationship('Owner', back_populates='pets')
    species = db.relationship('Species', back_populates='pets')
    breed = db.relationship('Breed', back_populates='pets')
    medical_records = db.relationship('MedicalRecord', back_populates='pet', lazy='dynamic')
    appointments = db.relationship('Appointment', back_populates='pet', lazy='dynamic')
    vaccination_records = db.relationship('VaccinationRecord', back_populates='pet', lazy='dynamic')
    deworming_records = db.relationship('DewormingRecord', back_populates='pet', lazy='dynamic')
    allergies = db.relationship('Allergy', back_populates='pet', lazy='dynamic')

    def __repr__(self):
        return f'<Pet {self.name}>'


class Allergy(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'allergies'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    allergen = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20))  # Mild, Moderate, Severe
    reaction = db.Column(db.Text)
    diagnosed_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    pet = db.relationship('Pet', back_populates='allergies')

    def __repr__(self):
        return f'<Allergy {self.allergen}>'
