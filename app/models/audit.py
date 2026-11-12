from datetime import UTC, datetime

from flask import request

from app.extensions import db


class AuditLog(db.Model):
    """Activity and audit trail tracking all major CRUD and authentication actions."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, RESTORE, LOGIN, LOGOUT
    entity_type = db.Column(db.String(50), nullable=False)  # Pet, Owner, Appointment, Invoice, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>'


def log_activity(action, entity_type, entity_id=None, details=None, user_id=None):
    """Utility helper to record an audit log entry."""
    try:
        from flask_login import current_user
        if user_id is None and current_user and current_user.is_authenticated:
            user_id = current_user.id
    except (RuntimeError, AttributeError):
        pass

    ip = None
    try:
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    except (RuntimeError, AttributeError):
        pass

    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip
    )
    db.session.add(log_entry)

