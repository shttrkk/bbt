from __future__ import annotations

from datetime import UTC, datetime


def validate_birth_date(value: str) -> bool:
    now = datetime.now(UTC)
    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue

        age = now.year - parsed.year
        return parsed.replace(tzinfo=UTC) <= now and 0 <= age <= 120

    return False
