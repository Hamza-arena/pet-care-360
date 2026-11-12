def test_app_starts(app):
    assert app is not None
    assert app.testing is True


def test_login_page_loads(client):
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'PetCare360' in response.data

