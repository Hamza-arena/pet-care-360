from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Owner(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'owners'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20), nullable=False)
    emergency_contact = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    national_id = db.Column(db.String(20))
    notes = db.Column(db.Text)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    addresses = db.relationship('OwnerAddress', backref='owner', lazy='dynamic')
    contacts = db.relationship('OwnerContact', backref='owner', lazy='dynamic')
    pets = db.relationship('Pet', backref='owner', lazy='dynamic')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __repr__(self):
        return f'<Owner {self.full_name}>'


class OwnerAddress(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'owner_addresses'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    address_type = db.Column(db.String(20), default='home')
    street_address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Pakistan')
    is_primary = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<OwnerAddress {self.address_type} - {self.city}>'


class OwnerContact(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = 'owner_contacts'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    contact_type = db.Column(db.String(20), nullable=False)
    contact_value = db.Column(db.String(120), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<OwnerContact {self.contact_type} - {self.contact_value}>'
