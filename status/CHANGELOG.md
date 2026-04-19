# Changelog

## [0.1.1] - 2026-04-19

### Changed

- проект финализирован в leak-aware постановке
- `result.csv` закреплён как финальный release artifact
- из репозитория удалены audit/probe/review/Codex-специфичные файлы
- документация переписана под реальное финальное состояние проекта
- `pyproject.toml` синхронизирован с версией `0.1.1`

### Added

- `quality/leak_context.py`
- leak-aware storage classification
- финальный defense document `PROJECT_STRUCTURE_FOR_DEFENSE.md`
- `parquet`-aware leak framing в основном контуре

### Release Notes

- задача интерпретируется как поиск suspicious / unjustified storage of personal data
- public/official/template документы не должны автоматически становиться positive
- fixed final `result.csv` остаётся главным deliverable для защиты и публикации

## [0.1.0] - 2026-04-18

### Added

- базовая структура проекта
- CLI scanner
- extractors / detectors / reporters
- explainable UZ classification
