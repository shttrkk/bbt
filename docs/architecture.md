# Architecture

## Source Of Truth

Текущая архитектура следует решениям из:

- `HACKATHON_PDN_ANALYSIS.md`
- `HACKATHON_SOLUTION_PLAN.md`

Ключевой baseline:

`scan -> detect format -> dispatch extractor -> normalize -> detect candidates -> validate -> aggregate -> classify(UZ) -> report`

## Pipeline

1. `scanner.walker`
   Рекурсивный обход каталога, сбор `FileDescriptor`, обработка ошибок доступа, пропуск скрытых путей по конфигу.
2. `scanner.format_detector`
   Определение формата по extension и опционально по MIME с graceful fallback.
3. `scanner.dispatcher`
   Routing `format -> extractor`, unsupported форматы не валят run.
4. `extractors.*`
   Извлечение текста и структуры из конкретного формата.
5. `normalize.*`
   Unicode/whitespace/value normalization и context windows.
6. `detectors.*`
   Поиск baseline-кандидатов ПДн по категориям.
7. `validators.*`
   Строгая валидация сущностей, где есть надежные алгоритмы.
8. `classify.uz_engine`
   Explainable rules engine для `УЗ-1..УЗ-4` и `NO_PDN`.
9. `reporting.*`
   Privacy-safe output в `CSV`, `JSON`, `Markdown`.

## Слои проекта

- `scanner`
  Технический слой traversal/routing.
- `extractors`
  Format-aware extraction layer.
- `normalize`
  Канонизация текста и значений.
- `detectors`
  Candidate generation по семействам `ordinary`, `government`, `payment`, `sensitive`.
- `validators`
  Независимые проверяемые валидаторы.
- `classify`
  Config-driven UZ classification.
- `reporting`
  Privacy-safe artifact generation.
- `runtime`
  Логирование, ошибки, метрики.

## Internal Data Flow

`FileDescriptor`
-> `ExtractedContent`
-> `DetectionResult[]`
-> `FileScanResult`
-> `RunSummary`

В `models.py` заданы единые typed-контракты между слоями. В persisted artifacts не сериализуются `raw_value` и `normalized_value`.

## Privacy-Safe Reporting

Принципы:

- raw PII не сохраняется в `CSV/JSON/Markdown`;
- для корреляции используются короткие salted hashes;
- `masked_preview` включается только при флаге `include_masked_samples`;
- логи не печатают полные совпадения;
- JSON report хранит только категории, counts, статусы, хэши, location hints и reason codes.

## UZ Classification

Классификация соответствует рекомендациям из аналитики:

- `УЗ-1`
  special/biometric signals;
- `УЗ-2`
  validated payment data или большой объем government IDs;
- `УЗ-3`
  presence government IDs или большой объем ordinary PII;
- `УЗ-4`
  ordinary PII малого объема;
- `NO_PDN`
  признаки ПДн не набрали заданные пороги.

Пороги вынесены в `configs/*.yaml`. Движок хранит `classification_reasons`, чтобы решение было explainable.

## Planned Hooks

Planned, но не fully implemented в `v0.1.0`:

- selective OCR для `image` и scanned `PDF`;
- legacy `DOC` fallback chain;
- `MP4` metadata/frame/subtitle extraction;
- anti-false-positive heuristics для шаблонов и public policy docs;
- chunked large-file processing для `Parquet/XLS/PDF`.
