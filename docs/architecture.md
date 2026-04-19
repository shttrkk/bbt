# Architecture

## Source Of Truth

Финальная поставка описана в [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md).

Актуальный submission-baseline:

`scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`

## Pipeline

1. `scanner.walker`
   Рекурсивный обход каталога и сбор `FileDescriptor`.
2. `scanner.format_detector`
   Определение формата по extension и опционально по MIME.
3. `scanner.dispatcher`
   Routing `format -> extractor`.
4. `extractors.*`
   В submission реально используются `txt`, `csv`, `json`, `html`.
5. `normalize.*`
   Нормализация текста, whitespace и значений.
6. `detectors.*`
   Поиск baseline-кандидатов ПДн.
7. `quality.*`
   Снижение false positives через template/public-doc/reference-data/noise suppression.
8. `classify.uz_engine`
   Explainable rules engine для `УЗ-1..УЗ-4` и `NO_PDN`.
9. `reporting.*`
   Privacy-safe output и сборка submission-артефакта.

## Submission-Relevant Components

- Extractors: `txt`, `csv`, `json`, `html`
- Detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`, `birth_date_candidate`
- Quality flags:
  - `is_template`
  - `is_public_doc`
  - `is_reference_data`
- Export rule:
  - в `result.csv` попадают только файлы с `assigned_uz != NO_PDN`

## Planned But Not Submission-Critical

В кодовой базе есть hooks или заглушки для:

- `pdf`
- `docx`
- `rtf`
- `xls/xlsx`
- `parquet`
- `image` / OCR
- `doc`
- `mp4`

Эти направления не были полноценными источниками финального submission-результата текущей версии.

## Privacy-Safe Reporting

- raw PII не сохраняется в `CSV/JSON/Markdown`
- итоговый submission использует только positive-only export
- отчеты сохраняют counts, categories, hashes, reason codes и quality-flags без полного раскрытия значений

## UZ Classification

- `NO_PDN`
  файл не набрал устойчивых PD signals после quality-layer
- `УЗ-4`
  ordinary PII малого объема
- `УЗ-3`
  government IDs или ordinary PII большего объема
- `УЗ-2`
  validated payment data или более рискованные government signals
- `УЗ-1`
  sensitive / biometric-like сигналы, если включены соответствующие detectors
