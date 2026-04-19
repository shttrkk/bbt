# Roadmap

## Submission Baseline

Финальный submission-проход описан в [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md).

Зафиксированное состояние:

- реальный submission-контур работает на `txt/csv/json/html`
- решающие улучшения относительно раннего baseline находятся в quality-layer
- в submission попадают только файлы с итоговым `assigned_uz != NO_PDN`

## v0.1.1 Submission Profile

- локальный CLI-проход для подготовки `result.csv`
- detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`, `birth_date_candidate`
- quality-layer:
  - template suppression
  - public-document suppression
  - reference-data suppression
  - HTML / JS / token-noise suppression
  - structured `id/token` noise suppression
- privacy-safe reporting
- positive-only export в legacy submission-формат `size,time,name`

## Pending After Submission

- реальные extractors для `pdf`, `docx`, `rtf`, `xls/xlsx`, `parquet`
- selective OCR для `tif/png/jpg/gif`
- scanned PDF fallback
- legacy `DOC` fallback chain
- best-effort `MP4` processing
- performance hardening для больших structured и document-heavy каталогов

## Practical Priority

1. Поддержать document/structured форматы, которые уже перечислены в конфиге, но пока остаются заглушками.
2. Сохранить текущий precision-first quality-layer при расширении coverage.
3. Не включать OCR и тяжелые extractors в core path без отдельной проверки влияния на false positives и throughput.
