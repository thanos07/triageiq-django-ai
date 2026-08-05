import pytest
from django.core.management.base import CommandError

from accounts.management.commands.seed_demo import Command
from accounts.models import User


@pytest.mark.django_db
def test_prepare_demo_user_creates_restricted_viewer(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEMO_EMAIL",
        "restricted-demo@example.com",
    )
    monkeypatch.setenv(
        "DEMO_PASSWORD",
        "RestrictedDemo123!",
    )
    monkeypatch.setenv(
        "DEMO_USERNAME",
        "restricted-demo",
    )
    monkeypatch.setenv(
        "DEMO_ROLE",
        User.Role.VIEWER,
    )

    user = Command()._prepare_demo_user()

    assert user.email == "restricted-demo@example.com"
    assert user.username == "restricted-demo"
    assert user.role == User.Role.VIEWER
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.check_password(
        "RestrictedDemo123!"
    )


@pytest.mark.django_db
def test_prepare_demo_user_demotes_existing_staff_account(
    monkeypatch,
):
    existing_user = User.objects.create_user(
        email="demo@example.com",
        username="existing-demo",
        password="OldPassword123!",
        role=User.Role.ADMIN,
        is_staff=True,
    )

    monkeypatch.setenv(
        "DEMO_EMAIL",
        existing_user.email,
    )
    monkeypatch.setenv(
        "DEMO_PASSWORD",
        "NewDemoPassword123!",
    )
    monkeypatch.setenv(
        "DEMO_USERNAME",
        existing_user.username,
    )
    monkeypatch.setenv(
        "DEMO_ROLE",
        User.Role.VIEWER,
    )

    updated_user = Command()._prepare_demo_user()
    updated_user.refresh_from_db()

    assert updated_user.pk == existing_user.pk
    assert updated_user.role == User.Role.VIEWER
    assert updated_user.is_staff is False
    assert updated_user.is_superuser is False
    assert updated_user.check_password(
        "NewDemoPassword123!"
    )


@pytest.mark.django_db
def test_prepare_demo_user_rejects_admin_role(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEMO_EMAIL",
        "unsafe-demo@example.com",
    )
    monkeypatch.setenv(
        "DEMO_PASSWORD",
        "UnsafeDemo123!",
    )
    monkeypatch.setenv(
        "DEMO_USERNAME",
        "unsafe-demo",
    )
    monkeypatch.setenv(
        "DEMO_ROLE",
        User.Role.ADMIN,
    )

    with pytest.raises(
        CommandError,
        match="cannot be assigned the administrator role",
    ):
        Command()._prepare_demo_user()

    assert not User.objects.filter(
        email="unsafe-demo@example.com",
    ).exists()


@pytest.mark.django_db
def test_prepare_demo_user_refuses_superuser_email(
    monkeypatch,
):
    superuser = User.objects.create_superuser(
        email="private-admin@example.com",
        username="private-admin",
        password="PrivateAdmin123!",
        role=User.Role.ADMIN,
    )

    monkeypatch.setenv(
        "DEMO_EMAIL",
        superuser.email,
    )
    monkeypatch.setenv(
        "DEMO_PASSWORD",
        "ReplacementPassword123!",
    )
    monkeypatch.setenv(
        "DEMO_USERNAME",
        superuser.username,
    )
    monkeypatch.setenv(
        "DEMO_ROLE",
        User.Role.VIEWER,
    )

    with pytest.raises(
        CommandError,
        match="belongs to a Django superuser",
    ):
        Command()._prepare_demo_user()

    superuser.refresh_from_db()

    assert superuser.is_staff is True
    assert superuser.is_superuser is True
    assert superuser.role == User.Role.ADMIN
    assert superuser.check_password(
        "PrivateAdmin123!"
    )


@pytest.mark.django_db
def test_prepare_demo_user_rejects_duplicate_username(
    monkeypatch,
):
    User.objects.create_user(
        email="existing@example.com",
        username="already-used",
        password="ExistingUser123!",
        role=User.Role.VIEWER,
    )

    monkeypatch.setenv(
        "DEMO_EMAIL",
        "new-demo@example.com",
    )
    monkeypatch.setenv(
        "DEMO_PASSWORD",
        "NewDemo123!",
    )
    monkeypatch.setenv(
        "DEMO_USERNAME",
        "already-used",
    )
    monkeypatch.setenv(
        "DEMO_ROLE",
        User.Role.VIEWER,
    )

    with pytest.raises(
        CommandError,
        match="already used by another account",
    ):
        Command()._prepare_demo_user()

    assert not User.objects.filter(
        email="new-demo@example.com",
    ).exists()