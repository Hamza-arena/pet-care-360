from app.routes.admin import admin_bp
from app.routes.appointments import appointments_bp
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.finance import finance_bp
from app.routes.laboratory import laboratory_bp
from app.routes.medical import medical_bp
from app.routes.owners import owners_bp
from app.routes.pets import pets_bp
from app.routes.pharmacy import pharmacy_bp
from app.routes.vaccination import vaccination_bp

__all__ = [
    'admin_bp',
    'appointments_bp',
    'auth_bp',
    'dashboard_bp',
    'finance_bp',
    'laboratory_bp',
    'medical_bp',
    'owners_bp',
    'pets_bp',
    'pharmacy_bp',
    'vaccination_bp'
]

