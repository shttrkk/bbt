# Project Structure For Defense

## 1. Что это за проект

`pdn-scanner` — локальная система анализа файлового хранилища, которая ищет не просто любые персональные данные, а рискованное и необоснованное хранение персональных данных.

Ключевая идея для защиты:

- проект решает задачу не как “NER по ПДн”
- проект решает задачу как “triage утечек и подозрительного хранения”

## 2. Технологический стек

- Python 3.11+
- Typer
- Pydantic
- PyYAML
- pandas / pyarrow
- pypdf
- pdfplumber
- python-docx
- striprtf
- openpyxl / xlrd
- pillow
- pytesseract
- orjson
- pytest

## 3. Верхнеуровневая структура репозитория

- `src/pdn_scanner/`
  основной код
- `tests/`
  тесты
- `configs/`
  конфиги запуска
- `docs/`
  архитектура и постановка
- `status/`
  release status / version / changelog
- `result.csv`
  финальный submission
- `SUBMISSION.md`
  описание финального deliverable

## 4. Pipeline по этапам

`scan -> detect format -> dispatch extractor -> detect -> quality-layer -> leak-context -> classify -> report`

Расшифровка:

1. `walker`
   обходит директорию
2. `format_detector`
   определяет формат
3. `dispatcher`
   выбирает extractor
4. `extractor`
   достаёт текст/структуру
5. `detector`
   находит кандидатные PD signals
6. `quality-layer`
   чистит шум и false positives
7. `leak-context`
   определяет storage context и жанр
8. `classifier`
   присваивает `TARGET_LEAK / JUSTIFIED / NON_TARGET` и UZ level
9. `reporting`
   пишет privacy-safe отчёты

## 5. Extractors

Модули:
- `txt.py`
- `csv.py`
- `json.py`
- `parquet.py`
- `pdf.py`
- `docx.py`
- `rtf.py`
- `xls.py`
- `html.py`
- `image.py`
- `office_legacy.py`

Как объяснять:
- text-like форматы дают самый устойчивый baseline
- structured форматы важны для subject-level exports
- document extractors важны для office/PDF хвоста
- image/PDF OCR включаются отдельными конфигами, потому что это самый дорогой и шумный путь

## 6. Detectors

Слои сигналов:

- ordinary:
  `person_name`, `address`, `phone`, `email`, `birth_date`, `birth_place`
- government:
  `snils`, `passport_*`, `inn_individual`, `inn_legal_entity`, `driver_license`, `mrz`
- payment:
  `bank_card`, `bank_account`, `bik`
- sensitive / biometric:
  специальные и биометрические признаки

Важно:
- одиночный weak signal не должен автоматически делать файл positive
- реальный смысл имеют anchor bundles и subject context

## 7. Validators

Что валидируем:
- `SNILS`
- `INN`
- `bank card / Luhn`
- банковские реквизиты
- даты рождения
- MRZ

Зачем это нужно:
- убрать ложные совпадения
- повысить доверие к hard anchors

## 8. Quality-Layer

Это один из самых важных модулей проекта.

Он отвечает за:
- подавление template-like файлов
- подавление public-doc хвоста
- подавление reference-data хвоста
- HTML noise suppression
- structured noise suppression
- format-specific guards для `pdf/docx/xls/image`

Главный тезис для защиты:

качество системы обеспечивается не только detector-ами, а тем, что после детекции идёт сильный анти-FP слой.

## 9. Leak-Aware Logic

Модуль: `quality/leak_context.py`

Что делает:
- определяет жанр документа
- считает риск
- считает оправданность хранения
- классифицирует storage context

Примеры жанров:
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

Ключевая идея:
- ПДн сами по себе не равны инциденту
- риск = ПДн вне оправданного контекста хранения

## 10. Classifier / UZ Logic

Модуль: `classify/uz_engine.py`

Два уровня решения:

1. storage decision
   `TARGET_LEAK / PD_BUT_JUSTIFIED_STORAGE / NON_TARGET`
2. risk level
   `UZ-1 .. UZ-4` или `NO_PDN`

Логика:
- justified и non-target подавляются в `NO_PDN`
- только `TARGET_LEAK` получает UZ level
- validated payment и sensitive data повышают уровень риска

## 11. OCR Branch

Модули:
- `extractors/ocr.py`
- `extractors/image.py`
- OCR hooks в `pdf.py`

Как работает:
- OCR включается конфигом
- используется shortlist/auto-logic
- есть несколько preprocessing variants
- есть несколько `psm` режимов tesseract

Как объяснять на защите:
- OCR есть
- он дорогой и шумный
- в финальный submission его вклад ограничен
- это не недоработка, а сознательный precision-first tradeoff

## 12. Cross-File Logic

Модуль: `submission/cross_file.py`

Зачем нужен:
- часть файлов по отдельности слабая
- но набор файлов в одной директории образует leak bundle

Что делает:
- демотит weak singletons
- промоутит person/address bundles across files
- учитывает shared hashes и small-directory bundles

Хороший пример для защиты:
- `customers.csv` и `logistics.csv` по отдельности слабее, чем вместе

## 13. Что считается Target Leak

- анкеты
- внутренние employee docs
- доверенности
- consent docs
- handover docs
- home-office / service request docs
- личная переписка
- subject-level exports физлиц
- фото/сканы документов
- заполненные персональные формы

## 14. Что считается Justified Storage

- публичные контакты сотрудников
- официальные contact docs
- public reports
- justified public disclosures
- public directories
- официальные документы с ответственными лицами

## 15. Какие уровни проверки есть в системе

1. File discovery
2. Format detection
3. Extraction
4. Entity detection
5. Validation
6. Quality suppression
7. Leak-context scoring
8. UZ classification
9. Cross-file correction
10. Privacy-safe reporting

## 16. Как рассказывать решение по слайдам

Слайд 1:
- задача и почему naive PD detection не работает

Слайд 2:
- архитектура pipeline

Слайд 3:
- extractors и supported formats

Слайд 4:
- detectors + validators

Слайд 5:
- quality-layer как основной anti-FP барьер

Слайд 6:
- leak-aware logic:
  genre
  risk
  justification
  storage class

Слайд 7:
- UZ classifier и explainable reasons

Слайд 8:
- cross-file logic

Слайд 9:
- OCR branch и почему она не доминирует в финальном submission

Слайд 10:
- финальный `result.csv` и почему именно он зафиксирован

## 17. Короткая формула защиты

Если нужно объяснить проект в одном абзаце:

`Мы построили не просто поиск ПДн по файлам, а многоступенчатую систему triage, которая сначала извлекает и валидирует сигналы, потом убирает public/template/reference шум, затем оценивает жанр и контекст хранения и только после этого решает, похож ли файл на реальную утечку или на оправданное хранение.`
