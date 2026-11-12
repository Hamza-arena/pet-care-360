from datetime import datetime, timezone
from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)

    def soft_delete(self, user_id=None):
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None

    @property
    def is_deleted(self):
        return self.deleted_at is not None

