"""Regression coverage for isolated deterministic Station 04."""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_station04_routes_and_data():
    home = client.get('/')
    assert home.status_code == 200
    assert 'href="/viber"' in home.text
    assert client.get('/viber').status_code == 200
    response = client.get('/api/viber-scenario')
    assert response.status_code == 200
    payload = response.json()
    assert payload['scenario_id'] == 'viber_takeover_001'
    assert payload['start_node'] == 'chat_opening'
    assert payload['variants'] == ['sms', 'flash_call']
    assert set(payload['endings']) == {'danger', 'safe', 'best_safe'}


def test_legacy_routes_survive_station04():
    for path in ('/call', '/sms', '/qr', '/api/sms-challenge', '/api/qr-challenge', '/api/health'):
        assert client.get(path).status_code == 200, path


def test_new_static_assets():
    for path in ('/static/js/viber.js', '/static/css/viber.css', '/static/css/home-station04.css'):
        response = client.get(path)
        assert response.status_code == 200
        assert response.content
