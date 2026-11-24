"""Тесты проверок прав по ролям."""
from services.permissions import is_admin, is_service


def test_is_admin_true():
    assert is_admin({'role': 'admin'}) is True


def test_is_admin_false_for_metodist():
    assert is_admin({'role': 'metodist'}) is False


def test_is_admin_false_without_role():
    assert is_admin({}) is False


def test_is_service_true():
    assert is_service({'is_service': True}) is True


def test_is_service_false():
    assert is_service({'is_service': False}) is False
    assert is_service({}) is False
