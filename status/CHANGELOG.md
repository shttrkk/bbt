# Changelog

Формат ориентирован на Keep a Changelog.

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
- валидаторы `Luhn`, `СНИЛС`, `ИНН`
- explainable `UZ` classifier
- privacy-safe reporters `CSV`, `JSON`, `Markdown`
- unit и smoke tests

### Changed

- `ocr.mode` в YAML-профилях зафиксирован как string, чтобы config loader не падал
- `report.json` больше не сериализует `extraction.text_chunks`
- phone/card/government detectors ужесточены против timestamp/UUID/identifier false positives
- ordinary detectors расширены schema-aware detection для `person_name` и `address`
- добавлены regression tests на false-positive / false-negative кейсы датасета

### Planned

- реальные extractors для `pdf/docx/rtf/xls/parquet`
- anti-false-positive heuristics
- selective OCR
- legacy `DOC` and best-effort `MP4`
- worker pool и performance tuning

### Not Yet Implemented

- OCR в core pipeline
- scanned PDF fallback
- public-doc suppression layer
- template-aware downscoring
- chunked parquet/xls processing
