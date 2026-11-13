try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC),
                           onupdate=lambda: datetime.now(UTC), nullable=False)


class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    deleted_by = db.Column(db.Integer, nullable=True)

    def soft_delete(self, user_id=None):
        self.deleted_at = datetime.now(UTC)
        self.deleted_by = user_id
        db.session.add(self)

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        db.session.add(self)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @classmethod
    def query_active(cls):
        """Standard query excluding soft-deleted records."""
        return cls.query.filter(cls.deleted_at.is_(None))

    @classmethod
    def query_deleted(cls):
        """Query returning only soft-deleted records (for Recycle Bin)."""
        return cls.query.filter(cls.deleted_at.is_not(None))

    @classmethod
    def count_active(cls):
        return cls.query_active().count()

    @classmethod
    def count_deleted(cls):
        return cls.query_deleted().count()


class TenantMixin:
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)

    @classmethod
    def query_for_clinic(cls, clinic_id):
        """Query active records belonging to a specific clinic."""
        return cls.query_active().filter(cls.clinic_id == clinic_id)

