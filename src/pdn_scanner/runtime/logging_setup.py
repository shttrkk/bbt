from __future__ import annotations

import logging

from rich.logging import RichHandler

from pdn_scanner.config import AppConfig


def setup_logging(config: AppConfig) -> None:
    level = getattr(logging, config.logging.level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=config.logging.rich_tracebacks,
                show_path=config.logging.show_path,
            )
        ],
        force=True,
    )
