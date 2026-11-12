from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Species(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'species'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

    breeds = db.relationship('Breed', backref='species', lazy='dynamic')

    def __repr__(self):
        return f'<Species {self.name}>'


class Breed(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'breeds'

    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    average_lifespan = db.Column(db.String(20))
    average_weight = db.Column(db.String(20))

    def __repr__(self):
        return f'<Breed {self.name}>'


class Pet(db.Model, SoftDeleteMixin, TimestampMixin):
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

    owner = db.relationship('Owner', backref=db.backref('pets', lazy='dynamic'))
    species = db.relationship('Species', backref=db.backref('pets', lazy='dynamic'))
    breed = db.relationship('Breed', backref=db.backref('pets', lazy='dynamic'))
    medical_records = db.relationship('MedicalRecord', backref='pet', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='pet', lazy='dynamic')
    vaccination_records = db.relationship('VaccinationRecord', backref='pet', lazy='dynamic')
    allergies = db.relationship('Allergy', backref='pet', lazy='dynamic')

    def __repr__(self):
        return f'<Pet {self.name}>'


class Allergy(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'allergies'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    allergen = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20))  # Mild, Moderate, Severe
    reaction = db.Column(db.Text)
    diagnosed_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Allergy {self.allergen}>'
