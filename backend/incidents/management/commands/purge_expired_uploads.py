from __future__ import annotations

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from incidents.services.retention_cleanup import (
    purge_expired_temporary_files,
)


class Command(BaseCommand):
    help = (
        "Delete expired temporary incident source files "
        "from object storage and mark their database "
        "records as deleted."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help=(
                "Maximum number of expired files to "
                "process in one execution."
            ),
        )

    def handle(self, *args, **options) -> None:
        limit = options["limit"]

        if limit < 1:
            raise CommandError(
                "--limit must be at least 1."
            )

        result = purge_expired_temporary_files(
            limit=limit,
        )

        message = (
            "Temporary-file cleanup completed: "
            f"scanned={result.scanned}, "
            f"deleted={result.deleted}, "
            f"failed={result.failed}"
        )

        if result.failed:
            self.stdout.write(
                self.style.WARNING(message)
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(message)
            )