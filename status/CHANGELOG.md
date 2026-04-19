# Changelog

Формат ориентирован на Keep a Changelog.

## [0.1.1] - 2026-04-19

### Changed

- markdown-документация синхронизирована с актуальным `SUBMISSION.md`
- в docs зафиксирован реальный submission-контур вместо старого roadmap-состояния
- явно разделены:
  - что реально использовалось в submission
  - что присутствует в коде как hook или stub

### Submission Baseline

- пайплайн зафиксирован как `scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`
- в submission реально используются extractors `txt`, `csv`, `json`, `html`
- detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`, `birth_date_candidate`
- `result.csv` собирается только из positive-файлов с `assigned_uz != NO_PDN`

### Quality Layer

- зафиксированы флаги `is_template`, `is_public_doc`, `is_reference_data`
- в документации отражено suppression-поведение для HTML/JS/token noise и structured `id/token` noise

### Not Part Of Current Submission

- `pdf/docx/xls/parquet/ocr` не описываются как полноценные источники текущего submission-результата
- legacy `DOC`, `MP4` и тяжелые document pipelines остаются на следующих этапах

## [0.1.0] - 2026-04-18

### Added

- production-like структура проекта под `src/`
- `Typer` CLI с командами `scan`, `validate-config`, `version`
- YAML-конфиги `default`, `fast`, `ocr`
- typed models и config contracts
- walker / format detector / dispatcher
- extractors для `txt`, `csv`, `json`, `html`
- stub extractors для `pdf/docx/rtf/xls/parquet/image/doc/mp4`
- detectors для `email`, `phone`, `card`, `SNILS`, `INN`
- explainable `UZ` classifier
- privacy-safe reporters `CSV`, `JSON`, `Markdown`
