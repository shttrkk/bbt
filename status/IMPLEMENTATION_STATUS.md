# Implementation Status

Статус ниже синхронизирован с актуальным `SUBMISSION.md` и текущим кодом.

## Реально используется в submission

| Область | Статус | Комментарий |
|---|---|---|
| CLI | done | локальный `scan`-проход для подготовки privacy-safe артефактов |
| Walker | done | recursive traversal с recoverable errors |
| Format detection | done | extension + optional MIME fallback |
| Dispatcher | done | format routing и unsupported fallback |
| TXT extractor | done | используется в submission |
| CSV extractor | done | используется в submission |
| JSON extractor | done | используется в submission |
| HTML extractor | done | используется в submission |
| Ordinary detectors | done | `email`, `phone`, `person_name`, `address`, `birth_date_candidate` |
| Government detectors | done | `SNILS`, `INN` |
| Payment detectors | done | `bank_card` |
| Quality layer | done | `is_template`, `is_public_doc`, `is_reference_data`, noise suppression |
| UZ classification | done | config-driven, explainable, с `NO_PDN` |
| Privacy-safe reporting | done | `summary.csv`, `report.json`, `report.md`, positive-only export для submission |

## Есть в коде, но не является полноценной частью текущего submission

| Область | Статус | Комментарий |
|---|---|---|
| PDF extractor | stub | есть только unsupported fallback с warning |
| DOCX extractor | stub | есть только unsupported fallback с warning |
| RTF extractor | stub | hook присутствует, extraction не реализован |
| XLS/XLSX extractor | stub | hook присутствует, extraction не реализован |
| Parquet extractor | stub | hook присутствует, extraction не реализован |
| Image extractor / OCR | stub | OCR configurable, но не часть current submission flow |
| Legacy DOC extractor | stub | planned fallback chain |
| Video extractor | stub | best-effort planned |

## Частично реализовано

| Область | Статус | Комментарий |
|---|---|---|
| Sensitive detectors | partial | conservative hooks, по умолчанию не core-path |
| Bank validators | partial | базовые helpers без полного production-grade checksum coverage |
| Date validators | partial | `birth_date` helper присутствует, не основной submission signal |
| MRZ validator | partial | интерфейс есть, фактически planned hook |

## Следующий практический шаг

- довести `pdf/docx/xls/parquet` до реального extraction layer
- расширять coverage только без потери текущего precision-first quality-layer
- включать OCR отдельно от базового submission-контура
