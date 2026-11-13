import os
import sys

# Replace '<your-username>' with your PythonAnywhere account username
USERNAME = os.environ.get('USER', 'your_username')
PROJECT_DIR = f'/home/{USERNAME}/pet-care-360'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Production Environment Settings
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'petcare360-production-secret-key-pyanywhere'

# Database Configuration:
# On PythonAnywhere Free tier, external TCP connections to Neon are restricted.
# SQLite works 100% out of the box without any external network dependency:
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = f'sqlite:///{PROJECT_DIR}/petcare360.db'

from wsgi import app as application
