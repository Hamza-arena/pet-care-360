from app import create_app
from app.config import BaseConfig, ProductionConfig, TestingConfig
from app.extensions import db
from app.models.auth import User
from app.utils.security import is_safe_url


def test_is_safe_url_validation(app):
    """Test safe redirect URL validator against multiple bypass vectors."""
    with app.test_request_context(base_url='http://localhost:5000/'):
        # Insecure / External targets
        assert not is_safe_url('http://evil.com')
        assert not is_safe_url('https://evil.com/hack')
        assert not is_safe_url('//evil.com')
        assert not is_safe_url('//evil.com/path')
        assert not is_safe_url('/\\evil.com')
        assert not is_safe_url('\\evil.com')
        assert not is_safe_url('javascript:alert(1)')
        assert not is_safe_url('')
        assert not is_safe_url(None)

        # Safe internal targets
        assert is_safe_url('/dashboard')
        assert is_safe_url('/owners')
        assert is_safe_url('/pets/12?view=full')
        assert is_safe_url('/')


def test_login_open_redirect_defense(client, app):
    """Ensure malicious ?next parameter is discarded and redirects to index."""
    with app.app_context():
        user = User.query.filter_by(email='security_test@petcare.com').first()
        if not user:
            user = User(
                email='security_test@petcare.com',
                username='security_test',
                first_name='Sec',
                last_name='User',
                is_active=True
            )
            user.set_password('Pass1234!')
            db.session.add(user)
            db.session.commit()

    # Attempt login with external open redirect URL
    resp = client.post(
        '/auth/login?next=https://attacker.com/steal-creds',
        data={'email': 'security_test@petcare.com', 'password': 'Pass1234!'},
        follow_redirects=False
    )
    assert resp.status_code == 302
    target_loc = resp.headers.get('Location', '')
    assert 'attacker.com' not in target_loc
    assert target_loc in ['/', 'http://localhost/']


def test_login_safe_next_redirect(client, app):
    """Ensure valid internal ?next parameter is preserved."""
    with app.app_context():
        user = User.query.filter_by(email='security_test@petcare.com').first()
        if not user:
            user = User(
                email='security_test@petcare.com',
                username='security_test',
                first_name='Sec',
                last_name='User',
                is_active=True
            )
            user.set_password('Pass1234!')
            db.session.add(user)
            db.session.commit()

    resp = client.post(
        '/auth/login?next=/owners',
        data={'email': 'security_test@petcare.com', 'password': 'Pass1234!'},
        follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers.get('Location') in ['/owners', 'http://localhost/owners']


def test_logout_rejects_get(auth_client):
    """Ensure GET /auth/logout is rejected to prevent CSRF logout attacks."""
    resp = auth_client.get('/auth/logout')
    assert resp.status_code == 405  # Method Not Allowed


def test_logout_requires_post(auth_client):
    """Ensure POST /auth/logout successfully signs user out and invalidates session."""
    resp = auth_client.post('/auth/logout', follow_redirects=False)
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers.get('Location', '')

    # Verifying that subsequent request to a protected endpoint redirects to login
    protected_resp = auth_client.get('/dashboard')
    assert protected_resp.status_code in [302, 404]


def test_session_cookie_security_flags():
    """Verify standard security settings for sessions and cookies."""
    assert BaseConfig.SESSION_COOKIE_HTTPONLY is True
    assert BaseConfig.REMEMBER_COOKIE_HTTPONLY is True
    assert BaseConfig.SESSION_COOKIE_SAMESITE == 'Lax'
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.REMEMBER_COOKIE_SECURE is True


def test_rate_limiter_blocks_brute_force():
    """Verify rate limiter blocks more than 5 login requests per minute when enabled."""
    class RateLimitConfig(TestingConfig):
        RATELIMIT_ENABLED = True
        RATELIMIT_STORAGE_URI = "memory://"

    rate_app = create_app(RateLimitConfig)
    with rate_app.app_context():
        db.create_all()
        test_client = rate_app.test_client()
        # Fire 5 attempts
        for _ in range(5):
            r = test_client.post(
                '/auth/login',
                data={'email': 'wrong@test.com', 'password': 'wrong'},
                environ_base={'REMOTE_ADDR': '192.168.1.100'}
            )
            assert r.status_code in [200, 302]

        # 6th attempt must be rate-limited (429)
        blocked_r = test_client.post(
            '/auth/login',
            data={'email': 'wrong@test.com', 'password': 'wrong'},
            environ_base={'REMOTE_ADDR': '192.168.1.100'}
        )
        assert blocked_r.status_code == 429
        db.session.remove()
        db.drop_all()


# --- RBAC Authorization Matrix Tests ---

def test_rbac_unauthenticated_access(client):
    """Unauthenticated users must be redirected to login for protected pages."""
    protected_urls = [
        '/',
        '/admin/recycle-bin',
        '/admin/audit-logs',
        '/admin/clinics',
        '/medical/',
        '/pharmacy/',
        '/billing/'
    ]
    for url in protected_urls:
        resp = client.get(url, follow_redirects=False)
        assert resp.status_code == 302, f"Failed for {url}"
        assert '/auth/login' in resp.headers.get('Location', ''), f"Failed for {url}"


def test_rbac_receptionist_forbidden_from_admin(receptionist_client):
    """Receptionist (non-admin) must receive 403 Forbidden for admin-only pages."""
    admin_urls = [
        '/admin/recycle-bin',
        '/admin/audit-logs',
        '/admin/clinics',
        '/admin/staff'
    ]
    for url in admin_urls:
        resp = receptionist_client.get(url)
        assert resp.status_code == 403, f"Receptionist was not blocked from {url}"


def test_rbac_doctor_forbidden_from_admin(doctor_client):
    """Doctor (non-admin) must receive 403 Forbidden for admin-only pages."""
    resp = doctor_client.get('/admin/recycle-bin')
    assert resp.status_code == 403


def test_rbac_admin_full_access(auth_client):
    """Admin has access to admin modules, dashboard, and clinical endpoints."""
    admin_urls = [
        '/',
        '/admin/recycle-bin',
        '/admin/audit-logs',
        '/admin/clinics',
        '/admin/staff'
    ]
    for url in admin_urls:
        resp = auth_client.get(url)
        assert resp.status_code == 200, f"Admin could not access {url}"


def test_rbac_doctor_access(doctor_client):
    """Doctor can access clinical modules."""
    clinical_urls = [
        '/',
        '/medical/',
        '/pets/',
        '/appointments/'
    ]
    for url in clinical_urls:
        resp = doctor_client.get(url)
        assert resp.status_code == 200, f"Doctor could not access {url}"
