"""Тесты валидации схемы регистрации пользователя."""
import pytest
from pydantic import ValidationError

from schemas.user import UserCreate


def _base(**over):
    data = dict(
        username='user1',
        email='user@example.com',
        password='password123',
        first_name='Иван',
        last_name='Иванов',
        pd_consent=True,
    )
    data.update(over)
    return data


def test_valid_user_create():
    u = UserCreate(**_base())
    assert u.username == 'user1'
    assert u.email == 'user@example.com'


def test_username_too_short():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(username='ab'))
    assert 'минимум 3' in str(e.value)


def test_username_too_long():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(username='a' * 31))
    assert 'слишком длинный' in str(e.value)


def test_username_invalid_chars():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(username='юзер'))
    assert 'латинские' in str(e.value)


def test_username_valid_special_chars():
    u = UserCreate(**_base(username='user_.-1'))
    assert u.username == 'user_.-1'


def test_email_invalid_format():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(email='not-an-email'))
    assert 'почт' in str(e.value).lower()


def test_email_too_long():
    long_email = 'a' * 46 + '@x.io'  # 51 символ (> 50)
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(email=long_email))
    assert 'слишком длинная' in str(e.value)


def test_password_too_short():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(password='short'))
    assert '8 символов' in str(e.value)


def test_first_name_empty():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(first_name='   '))
    assert 'обязательно' in str(e.value)


def test_last_name_too_long():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(last_name='я' * 31))
    assert 'слишком длинное' in str(e.value)


def test_middle_name_optional():
    u = UserCreate(**_base(middle_name=None))
    assert u.middle_name is None


def test_middle_name_too_long():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(middle_name='о' * 31))
    assert 'слишком длинное' in str(e.value)


def test_consent_required():
    with pytest.raises(ValidationError) as e:
        UserCreate(**_base(pd_consent=False))
    assert 'согласие' in str(e.value).lower()


def test_role_is_ignored_for_public_registration():
    # role в модели есть, но сервис всё равно ставит методиста (проверяется в user_service)
    u = UserCreate(**_base(role='admin'))
    assert u.role.value == 'admin'  # схема пропускает, сервис переопределит
