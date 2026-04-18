# Implementation Status

## Реализовано

| Область | Статус | Комментарий |
|---|---|---|
| Project skeleton | done | `src/`, configs, docs, status files, tests |
| CLI | done | `scan`, `validate-config`, `version` |
| Config loader | done | YAML + typed models |
| Walker | done | recursive traversal с recoverable errors |
| Format detection | done | extension + optional MIME fallback |
| Dispatcher | done | format routing и unsupported fallback |
| TXT extractor | done | базовое чтение текста |
| CSV extractor | done | baseline row-oriented extraction |
| JSON extractor | done | baseline flattening |
| HTML extractor | done | visible text extraction |
| Luhn validator | done | unit-tested |
| SNILS validator | done | unit-tested |
| INN validator | done | unit-tested |
| UZ classification | done | config-driven, explainable |
| Privacy-safe reporting | done | CSV/JSON/MD без raw PII |

## Частично реализовано

| Область | Статус | Комментарий |
|---|---|---|
| Detectors | partial | baseline категории + schema-aware `person_name` / `address`, без advanced anti-false-positive слоя |
| Sensitive detection | partial | conservative hooks, по умолчанию выключено |
| Template heuristics | partial | только lightweight flagging |
| Metrics | partial | базовые run counters |

## Заглушки / Planned

| Область | Статус | Комментарий |
|---|---|---|
| PDF extractor | stub | интерфейс готов, реализация позже |
| DOCX extractor | stub | интерфейс готов, реализация позже |
| RTF extractor | stub | интерфейс готов, реализация позже |
| XLS/XLSX extractor | stub | интерфейс готов, реализация позже |
| Parquet extractor | stub | интерфейс готов, реализация позже |
| Image extractor | stub | OCR hook заложен |
| Legacy DOC extractor | stub | planned fallback chain |
| Video extractor | stub | best-effort planned |
| Date / bank / MRZ validators | stub | интерфейсы заложены |

## Не начинали

- worker pool / concurrency
- timeout management
- scanned PDF OCR fallback
- public policy / rules suppression layer
- goldset / benchmark harness
- cross-file correlation

## Следующая версия

В `v0.2.0` войдут:

- реальные extractors для `pdf/docx/rtf/xls/parquet`
- richer detection context
- anti-false-positive rules
- улучшенная per-file aggregation
- более детальный JSON report
