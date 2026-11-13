import datetime as _dt
import os
import shutil
import sys

if not hasattr(_dt, 'UTC'):
    _dt.UTC = _dt.timezone.utc

# Locate project directory reliably on PythonAnywhere
POSSIBLE_DIRS = [
    '/home/hamzaabubaker/pet-care-360',
    os.path.expanduser('~/pet-care-360'),
    os.path.abspath(os.path.dirname(__file__)),
]

PROJECT_DIR = None
for p in POSSIBLE_DIRS:
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, 'wsgi.py')):
        PROJECT_DIR = p
        break

if not PROJECT_DIR:
    PROJECT_DIR = '/home/hamzaabubaker/pet-care-360'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Switch working directory to project root so relative operations never default to /var/www
try:
    os.chdir(PROJECT_DIR)
except Exception:
    pass

# Production Environment Settings
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'petcare360-production-secret-key-pyanywhere'
os.environ['SESSION_COOKIE_SECURE'] = 'false'
os.environ['REMEMBER_COOKIE_SECURE'] = 'false'

# Database Configuration:
DB_PATH = os.path.join(PROJECT_DIR, 'petcare360.db')
DEV_DB_PATH = os.path.join(PROJECT_DIR, 'petcare360_dev.db')

# If petcare360.db doesn't exist yet but petcare360_dev.db exists, clone it automatically
if not os.path.exists(DB_PATH) and os.path.exists(DEV_DB_PATH):
    try:
        shutil.copyfile(DEV_DB_PATH, DB_PATH)
    except Exception:
        pass

os.environ['DATABASE_URL'] = f'sqlite:///{DB_PATH}'

from wsgi import app as application


