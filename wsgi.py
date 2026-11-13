import datetime as _dt
import os

if not hasattr(_dt, 'UTC'):
    _dt.UTC = _dt.timezone.utc

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

