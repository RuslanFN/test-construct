"""Тесты сида администратора (создание и синхронизация пароля)."""
import config
import seed
from security import verify_password
from tests.conftest import make_user_doc


async def test_ensure_admin_creates(fake_db):
    fake_db['users']._docs.clear()
    await seed.ensure_admin()
    admins = [u for u in fake_db['users']._docs if u['username'] == config.admin_username]
    assert len(admins) == 1
    admin = admins[0]
    assert admin['role'] == 'admin'
    assert admin['is_service'] is True
    assert verify_password(config.admin_password, admin['hashed_password'])


async def test_ensure_admin_idempotent(fake_db):
    fake_db['users']._docs.clear()
    await seed.ensure_admin()
    await seed.ensure_admin()
    admins = [u for u in fake_db['users']._docs if u['username'] == config.admin_username]
    assert len(admins) == 1


async def test_ensure_admin_syncs_password(fake_db):
    fake_db['users']._docs.clear()
    # заранее кладём админа со старым паролем
    stale = make_user_doc(
        username=config.admin_username, role='admin', password='old-password'
    )
    stale['is_service'] = True
    fake_db['users']._docs.append(stale)

    await seed.ensure_admin()

    admin = next(u for u in fake_db['users']._docs if u['username'] == config.admin_username)
    # пароль синхронизирован с config.admin_password
    assert verify_password(config.admin_password, admin['hashed_password'])
    # роль и is_service на месте
    assert admin['role'] == 'admin'
    assert admin['is_service'] is True


async def test_ensure_admin_promotes_role(fake_db):
    fake_db['users']._docs.clear()
    wrong_role = make_user_doc(username=config.admin_username, role='metodist')
    fake_db['users']._docs.append(wrong_role)
    await seed.ensure_admin()
    admin = next(u for u in fake_db['users']._docs if u['username'] == config.admin_username)
    assert admin['role'] == 'admin'
