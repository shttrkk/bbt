# Roadmap

## v0.1.0

- Локальный production-like каркас под `venv` и `Python 3.11+`.
- CLI `pdn-scan` с командами `scan`, `validate-config`, `version`.
- YAML configs и typed config loader.
- Walker, format detection, extractor dispatcher.
- Рабочие extractors `txt/csv/json/html`.
- Stub extractors для остальных форматов.
- Baseline detectors `email/phone/card/SNILS/INN`.
- Валидаторы `Luhn`, `СНИЛС`, `ИНН`.
- Explainable UZ engine.
- Privacy-safe reporting в `CSV/JSON/Markdown`.
- Unit tests + CLI smoke test.

## v0.2.0

- Реальные extractors: `pdf`, `docx`, `rtf`, `xls/xlsx`, `parquet`.
- Более богатый context scoring.
- Anti-false-positive rules для:
  - шаблонов документов;
  - public privacy/rules/terms документов;
  - шумных HTML.
- Расширенная агрегация:
  - `rows_affected`;
  - `validated_occurrences`;
  - `unique_hashes`.
- Улучшенная explainability в JSON report.

## v0.3.0

- Selective OCR для `tif/png/jpg/gif`.
- OCR fallback для scanned `PDF`.
- Best-effort legacy `DOC`.
- Best-effort `MP4` metadata/subtitle/frame hooks.
- Performance hardening:
  - bounded memory;
  - chunked structured scanning;
  - worker pool;
  - timeouts / graceful degradation.

## Optional Stretch Goals

- Goldset и benchmark harness.
- Resume/incremental scan artifacts.
- Cross-file correlation по HMAC hashes.
- Demo dataset и classification fixtures.
- Более формализованный template/public-doc suppression layer.
