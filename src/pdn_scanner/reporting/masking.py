from __future__ import annotations

import hashlib
import hmac
import os

from pdn_scanner.config import AppConfig


def hash_value(value: str, config: AppConfig) -> str | None:
    if not config.masking.enabled or not value:
        return None

    secret = os.getenv(config.masking.secret_env_var, config.masking.default_salt).encode("utf-8")
    digest = hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[: config.masking.hash_length]


def mask_preview(value: str, config: AppConfig) -> str | None:
    if not value or not config.feature_flags.include_masked_samples:
        return None

    prefix = config.masking.preview_prefix
    suffix = config.masking.preview_suffix

    if len(value) <= prefix + suffix:
        return "*" * len(value)

    hidden = "*" * max(1, len(value) - prefix - suffix)
    return f"{value[:prefix]}{hidden}{value[-suffix:]}"
