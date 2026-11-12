from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Clinic(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'clinics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    license_number = db.Column(db.String(50))
    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    is_active = db.Column(db.Boolean, default=True)
    currency = db.Column(db.String(10), default='PKR', nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), default=16.00, nullable=False)
    invoice_sequence = db.Column(db.Integer, default=0, nullable=False)

    departments = db.relationship('Department', backref='clinic', lazy='dynamic')
    rooms = db.relationship('Room', backref='clinic', lazy='dynamic')

    def __repr__(self):
        return f'<Clinic {self.name}>'


class Department(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    head_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)

    rooms = db.relationship('Room', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name}>'


class Room(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    room_number = db.Column(db.String(20), nullable=False)
    room_type = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    capacity = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<Room {self.room_number}>'


class DoctorSchedule(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'doctor_schedules'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_appointments = db.Column(db.Integer, default=20)
    is_available = db.Column(db.Boolean, default=True)

    doctor = db.relationship('User', backref='schedules', foreign_keys=[doctor_id])
    clinic = db.relationship('Clinic', backref='doctor_schedules')

    def __repr__(self):
        return f'<DoctorSchedule doctor={self.doctor_id} day={self.day_of_week}>'
