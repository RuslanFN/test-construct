"""Интеграционные тесты /api/admin: доступ, пользователи, тесты."""
import uuid

from tests.conftest import make_test_doc, make_user_doc


def test_admin_requires_auth(api_client):
    assert api_client.get('/api/admin/tests').status_code == 401


def test_admin_requires_admin_role(api_client, metodist_doc, auth_headers):
    resp = api_client.get('/api/admin/tests', headers=auth_headers(metodist_doc))
    assert resp.status_code == 403


def test_admin_tests_list(api_client, admin_doc, metodist_doc, auth_headers, fake_db):
    fake_db['tests']._docs.append(make_test_doc(author_id=metodist_doc['_id'], title='X'))
    resp = api_client.get('/api/admin/tests', headers=auth_headers(admin_doc))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_admin_tests_status_filter(api_client, admin_doc, auth_headers, fake_db):
    fake_db['tests']._docs.append(make_test_doc(author_id=uuid.uuid4(), title='D', status='draft'))
    fake_db['tests']._docs.append(make_test_doc(author_id=uuid.uuid4(), title='P', status='published'))
    resp = api_client.get('/api/admin/tests?status=published', headers=auth_headers(admin_doc))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_admin_users_list(api_client, admin_doc, metodist_doc, auth_headers):
    resp = api_client.get('/api/admin/users', headers=auth_headers(admin_doc))
    assert resp.status_code == 200
    usernames = {u['username'] for u in resp.json()}
    assert 'admin' in usernames
    assert 'metodist' in usernames


def test_admin_block_user(api_client, admin_doc, auth_headers, fake_db):
    target = make_user_doc(username='victim')
    fake_db['users']._docs.append(target)
    resp = api_client.patch(
        f"/api/admin/users/{target['_id']}",
        json={'is_active': False},
        headers=auth_headers(admin_doc),
    )
    assert resp.status_code == 204
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['is_active'] is False


def test_admin_approve_user(api_client, admin_doc, auth_headers, fake_db):
    target = make_user_doc(username='pend', approval_status='pending', is_active=False)
    fake_db['users']._docs.append(target)
    resp = api_client.patch(
        f"/api/admin/users/{target['_id']}",
        json={'approval_status': 'approved'},
        headers=auth_headers(admin_doc),
    )
    assert resp.status_code == 204
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['approval_status'] == 'approved'
    assert doc['is_active'] is True


def test_admin_delete_user(api_client, admin_doc, auth_headers, fake_db):
    target = make_user_doc(username='del')
    fake_db['users']._docs.append(target)
    resp = api_client.delete(
        f"/api/admin/users/{target['_id']}", headers=auth_headers(admin_doc)
    )
    assert resp.status_code == 204
    assert not any(u['username'] == 'del' for u in fake_db['users']._docs)


def test_admin_cannot_delete_service(api_client, admin_doc, auth_headers):
    resp = api_client.delete(
        f"/api/admin/users/{admin_doc['_id']}", headers=auth_headers(admin_doc)
    )
    assert resp.status_code == 403
