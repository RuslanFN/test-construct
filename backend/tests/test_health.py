"""Простейшая проверка, что приложение поднимается и health отвечает."""


def test_health(api_client):
    resp = api_client.get('/api/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


def test_lifespan_creates_admin(api_client, fake_db):
    # lifespan вызывает seed.ensure_admin — админ должен появиться в fake БД
    assert any(u.get('is_service') for u in fake_db['users']._docs)
