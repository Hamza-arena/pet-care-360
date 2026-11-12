from datetime import UTC, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class User(UserMixin, SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)

    # Relationships
    user_roles = db.relationship('UserRole', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')
    staff_profile = db.relationship('StaffProfile', backref='user', uselist=False,
                                    cascade='all, delete-orphan')

    @property
    def roles(self):
        return [ur.role for ur in self.user_roles.all()]

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def active(self):
        return self.is_active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(
            role.name.lower() == role_name.lower()
            for role in self.roles
        )

    def has_permission(self, permission_name):
        for role in self.roles:
            for rp in role.role_permissions:
                if rp.permission.name == permission_name:
                    return True
        return False

    def __repr__(self):
        return f'<User {self.username}>'


class Role(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    # Relationships
    user_roles = db.relationship('UserRole', backref='role', lazy='dynamic',
                                 cascade='all, delete-orphan')
    role_permissions = db.relationship('RolePermission', backref='role', lazy='dynamic',
                                      cascade='all, delete-orphan')

    @property
    def users(self):
        return [ur.user for ur in self.user_roles.all()]

    @property
    def permissions(self):
        return [rp.permission for rp in self.role_permissions.all()]

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(TimestampMixin, db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    # Relationships
    role_permissions = db.relationship('RolePermission', backref='permission', lazy='dynamic',
                                      cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Permission {self.name}>'


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    __table_args__ = (
        db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)

    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'


class StaffProfile(SoftDeleteMixin, TimestampMixin, db.Model):
    __tablename__ = 'staff_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    employee_id = db.Column(db.String(20), unique=True)
    department = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer)
    bio = db.Column(db.Text)

    def __repr__(self):
        return f'<StaffProfile employee_id={self.employee_id}>'
