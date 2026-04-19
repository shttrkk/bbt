# Architecture

## Цель архитектуры

Архитектура проекта заточена под explainable анализ файлового хранилища с leak-aware интерпретацией.

Главный вопрос системы:

`является ли файл подозрительным примером хранения персональных данных`

а не:

`встречаются ли в файле какие-либо персональные поля`

## Top-Level Pipeline

`scan -> detect format -> dispatch extractor -> detect -> quality-layer -> leak-context -> classify -> report`

## Основные слои

### 1. Scanner

- `scanner.walker`
  рекурсивно обходит каталог и строит `FileDescriptor`
- `scanner.format_detector`
  определяет формат по extension и MIME
- `scanner.dispatcher`
  выбирает extractor по `FileFormat`

### 2. Extractors

Модуль: `src/pdn_scanner/extractors/`

Реализованные extractor-ветки:
- `txt`
- `csv`
- `json`
- `parquet`
- `pdf`
- `docx`
- `rtf`
- `xls/xlsx`
- `html`
- `image`
- `doc`

Подход:
- structured extractors сохраняют row/header context
- document extractors извлекают page/chunk text
- `pdf` использует `pypdf` + `pdfplumber` fallback и selective OCR
- `image` использует OCR при включённом конфиге
- legacy `doc` проходит через отдельный extractor

### 3. Detection Layer

Модуль: `src/pdn_scanner/detectors/`

Группы сигналов:
- ordinary
  `person_name`, `address`, `phone`, `email`, `birth_date`, `birth_place`
- government
  `snils`, `passport_*`, `inn_individual`, `inn_legal_entity`, `driver_license`, `mrz`
- payment
  `bank_card`, `bank_account`, `bik`
- special
  health / beliefs / other special categories
- biometric
  biometric-like markers

Каждая находка содержит:
- category
- family
- confidence
- validation status
- masked preview / hash
- occurrences
- location hints
- context keywords

### 4. Validators

Модуль: `src/pdn_scanner/validators/`

Используются для снижения FP:
- `snils`
- `inn`
- `luhn`
- `bank`
- `dates`
- `mrz`

### 5. Quality Layer

Модуль: `src/pdn_scanner/quality/anti_fp.py`

Задача quality-layer:
- убрать шум
- подавить public/template/reference cases
- сохранить только meaningful subject-linked signals

Основные механизмы:
- template detection
- public document detection
- reference data detection
- HTML noise suppression
- structured `id/token` suppression
- schema-based confidence boost
- format-specific gates:
  `html`, `xls`, `docx`, `office`, `pdf`, `image`

### 6. Leak Context Layer

Модуль: `src/pdn_scanner/quality/leak_context.py`

Здесь система переходит от `PD presence` к `storage risk`.

Сначала определяется жанр документа:
- `personal_form`
- `internal_employee_doc`
- `personal_export`
- `public_contact_doc`
- `public_report`
- `blank_template`
- `org_requisites_doc`
- `image_of_personal_doc`
- `correspondence`
- `company_export`

Потом считаются:
- `risk_score`
- `justification_score`
- `noise_score`

На выходе файл получает один из storage classes:
- `TARGET_LEAK`
- `PD_BUT_JUSTIFIED_STORAGE`
- `NON_TARGET`

### 7. Classifier / UZ Logic

Модуль: `src/pdn_scanner/classify/uz_engine.py`

UZ-классификатор работает только поверх quality/leak-context решения.

Правила:
- justified/non-target storage уходит в `NO_PDN`
- target leak получает `UZ-1..UZ-4` в зависимости от family и объёма
- sensitive/biometric -> `UZ-1`
- validated payment -> `UZ-2`
- government-heavy -> `UZ-2/UZ-3`
- ordinary subject-linked bundles -> `UZ-4`

### 8. Cross-File Logic

Модуль: `src/pdn_scanner/submission/cross_file.py`

Нужен для случаев, когда единичный файл слабый, а директория в целом образует leak-bundle.

Механики:
- demotion weak singletons
- promotion structured pair bundles
- promotion by shared linkage hashes
- small-directory bundle promotion

### 9. Reporting

Модуль: `src/pdn_scanner/reporting/`

Типы отчётов:
- `summary.csv`
- `result.csv` runtime artifact
- `report.json`
- `report.md`

Свойства:
- privacy-safe serialization
- без raw PII
- explainable reasons и counters

## Финальный release state

Несмотря на широкий кодовый coverage, финальный конкурсный [result.csv](/Users/shttrkk/Downloads/ПДнDataset/result.csv) закреплён вручную как release artifact.

Это разделяет:
- runnable scanner
- финальное конкурсное решение

Именно это состояние и должно использоваться на защите.
