from __future__ import annotations

from datetime import datetime


def validate_birth_date(value: str) -> bool:
    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue

        age = datetime.utcnow().year - parsed.year
        return parsed <= datetime.utcnow() and 0 <= age <= 120

    return False
