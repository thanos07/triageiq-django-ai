# Django migration consistency

TriageIQ pins Django to `5.2.16` and commits every generated migration.

The custom `accounts.User` model inherits fields from Django's `AbstractUser`. Django 5.2.16's definitions of `groups` and `is_active` include updated help text compared with the original migration snapshot. Migration `accounts/0002_sync_abstract_user_fields.py` aligns the historical migration state with those inherited definitions.

This migration is metadata-only on ordinary supported databases: it does not add or remove the `groups` relation or the `is_active` column. It records the current field options so Django's migration autodetector remains clean.

Run the same checks locally that CI runs:

```bash
cd backend
pip install -r requirements-dev.txt
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
pytest
```

The first command should print `No changes detected` and exit successfully.

Do not edit `0001_initial.py` after it has been applied. Future Django upgrades should be intentional: update the exact pin, run `makemigrations --check --dry-run`, create any required migration, and run the complete test suite.
