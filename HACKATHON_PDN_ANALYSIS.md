# Workspace Audit

Текущая рабочая директория `/Users/shttrkk/Documents/МИРЭА/samshack` пуста: нет git-репозитория, кода, README, зависимостей или заготовок. Значит анализ ниже для greenfield-реализации.

Что это значит practically:
- Использовать существующий код сейчас нечего.
- Технический долг пока нулевой, но и ускорителей нет.
- Самый разумный путь: сразу закладывать модульную, но не переусложненную архитектуру под хакатон.

Где я уверен:
- В базовой архитектуре пайплайна, приоритетах MVP, валидаторах, privacy-safe reporting, test strategy.

Где это гипотеза без реального датасета:
- Доля сканов vs цифровых документов.
- Реальная ценность OCR для итогового score.
- Что организаторы считают “большим объемом” для УЗ-2/УЗ-3.
- Насколько глубоко реально нужно поддержать `DOC`, `XLS` и особенно `MP4`.

---

# A. Executive Summary

Это не задача “про AI”, а задача про надежный data-processing pipeline для heterogeneous file corpus с сильным уклоном в precision, validation и privacy-safe reporting.

Главный technical core:
- корректно извлечь текст/структуру из разных форматов;
- найти кандидатов rule-based способом;
- жестко валидировать то, что можно валидировать;
- аккуратно снижать false positive через контекст, нормализацию и конфигурируемые правила;
- присвоить УЗ по формализованному rules engine;
- выдать воспроизводимый отчет без утечки сырых ПДн.

Главный риск:
- сделать “широкую” поддержку форматов и сущностей, но получить лавину false positive, нестабильный OCR и плохую классификацию УЗ.

На чем можно выиграть:
- сильные валидаторы;
- fallback extraction pipeline;
- OCR только по триггерам, а не на все подряд;
- понятный per-file report + global summary;
- демонстрация, что решение не падает на битых файлах и не светит ПДн.

Рекомендуемый общий подход:
- брать modular balanced architecture;
- baseline = parsing + regex/heuristics + validators + configurable rules;
- OCR включать выборочно;
- LLM/NER не ставить в core path, только как optional second-pass на узкие кейсы.

---

# B. Design / Architecture Review

## Общая архитектура

Рекомендуемый pipeline:

`Walker -> Format Detection -> Extractor -> Normalizer -> Candidate Detectors -> Validators -> Aggregator -> UZ Engine -> Reporters`

## Подсистемы

| Подсистема | Назначение | Вход / Выход | Основные сложности | Риски | Приоритет | MVP / Later |
|---|---|---|---|---|---|---|
| Directory traversal / scanner | Рекурсивный обход хранилища | path -> stream of file jobs | 3000+ файлов, mixed tree, symlink loops, hidden files | зависание на спецфайлах, дубликаты | P0 | MVP |
| Format detection | Определить реальный тип файла | file path/bytes -> format enum | неверные расширения, контейнерные форматы | неправильный extractor | P0 | MVP |
| Extractors: structured | CSV/JSON/Parquet/XLS parsing | file -> rows/text chunks | большие объемы, кодировки, memory | OOM, пропуски строк | P0 | MVP |
| Extractors: documents | PDF/DOC/DOCX/RTF/HTML | file -> text/pages/tables | битые PDF, бинарный DOC, layout loss | low recall, parser crashes | P0 | MVP |
| Extractors: image/OCR | JPEG/PNG/GIF/TIF, scanned docs | image/page -> text | OCR latency, quality, rus/eng mixing | time sink, noise | P1 | later in depth |
| Extractors: video | MP4 metadata/frame sampling | video -> text/frames/subtitles | низкий ROI, высокий cost | сжечь время | P3 | best-effort only |
| Normalization pipeline | привести текст и значения к нормальной форме | raw text -> normalized text/candidates | Unicode, NBSP, separators, line breaks | missed matches | P0 | MVP |
| Candidate detectors | найти потенциальные ПДн | text/rows -> detections | разные форматы записи, ambiguity | false positive | P0 | MVP |
| Validators | подтвердить то, что можно проверить | candidate -> valid/invalid/unknown | доменные алгоритмы, edge cases | ложные срабатывания | P0 | MVP |
| Context engine | использовать соседние слова/колонки/ячейки | candidate + context -> confidence | баланс recall/precision | хрупкие эвристики | P1 | MVP-lite |
| UZ assignment engine | присвоить уровень защищенности | file summary -> UZ | “большой/малый объем” не формализован | спорные кейсы | P0 | MVP |
| Privacy-safe reporting | отчеты без сырых ПДн | results -> CSV/JSON/MD | полезность без утечки значений | либо leak, либо useless report | P0 | MVP |
| Logging / error handling | не падать и оставлять следы | all stages -> logs/errors | corrupted files, parser exceptions | crash of whole scan | P0 | MVP |
| Performance layer | ускорение и bounded memory | jobs -> concurrent execution | OCR/PDF CPU-heavy, DataFrame-heavy | slow scans | P1 | MVP-lite |
| Optional AI/LLM layer | second-pass на ambiguous text | masked snippets -> label/explanation | privacy, nondeterminism, latency | score regression | P3 | later only |

## Что важно по приоритету

P0:
- scanner
- robust extractors for core formats
- detectors + validators
- UZ engine
- reporting
- continue-on-error

P1:
- OCR auto-mode
- concurrency
- better context scoring
- performance tuning

P3:
- MP4 depth
- LLM/NER adjudication
- RAG/search UI

---

# C. Requirements Breakdown

## 1. Обязательные требования

- Рекурсивный обход файлового хранилища.
- Поддержка основных форматов из ТЗ.
- Извлечение данных из structured и unstructured sources.
- Детекция категорий ПДн.
- Классификация УЗ.
- Отчет с путем, категориями, counts, УЗ, форматом.
- Выходные форматы `CSV`, `JSON`, `Markdown`.
- CLI запуск.
- Обработка ошибок чтения файлов.
- Отсутствие ручного вмешательства.
- Воспроизводимость.
- Не хранить сырые ПДн в отчетах.

## 2. Желательные требования

- OCR для изображений и сканов.
- Несколько fallback extractor-цепочек для PDF/DOC.
- Валидация `Лун`, `СНИЛС`, `ИНН`, банковских реквизитов.
- Корректная работа на больших structured files.
- Нормализация разных форм записи.
- Конфигурируемые thresholds и правила.

## 3. Nice-to-have

- MIME detection, а не только extension-based routing.
- Пер-файловые confidence levels.
- Incremental JSONL results и resume/re-run удобство.
- Synthetic dataset generator и benchmark harness.
- Cross-file correlation по HMAC hash.
- Optional local NER/LLM on ambiguous snippets.
- HTML dashboard или web UI.

## 4. Рискованные / размытые требования

- Поддержка `DOC` и `MP4` “по-настоящему глубоко”.
- Что считать “большим объемом”.
- Насколько агрессивно надо искать адреса.
- Нужно ли извлекать ПДн из изображений внутри PDF, если PDF уже текстовый.
- Нужно ли считать generic mention special-category terms без привязки к человеку.

## 5. Скрытые требования из критериев оценки

- Precision важнее “широких, но шумных” детекторов.
- Нужен explainability: почему сущность найдена и почему УЗ такой.
- Нужно выживать на поврежденных файлах.
- Нужно не съедать память на больших таблицах.
- Нужно показать управляемость false positive.
- Нужна reproducible env setup.
- Нужны demo-friendly artifacts: summary, top risky files, error stats.

## Что критично для баллов

- Validators и context-aware detection.
- Четкий rules engine для УЗ.
- Fast-fail на одном файле не должен валить весь scan.
- Хороший privacy-safe report.
- OCR только если дает реальную прибавку, а не ломает throughput.

## Что можно упростить

- MP4 сделать best-effort.
- Не строить UI в первой итерации.
- Не делать ML-классификатор для всего.
- Не пытаться делать идеальное NER для ФИО/адресов с первого часа.

## Что не стоит переусложнять

- Распределенная обработка.
- RAG по сырым документам.
- Онтологии адресов, глубокий NLP на морфологии, knowledge graph.
- Суперсложный risk scoring вместо простого explainable rules engine.

---

# D. Scoring Strategy

## 1. Точность обнаружения ПДн — 40%

Что реально влияет:
- строгие валидаторы для числовых идентификаторов;
- контекстные триггеры для рискованных сущностей;
- нормализация текста и separators;
- structured-data aware scanning по column names и cells.

Что убивает оценку:
- любой `16-digit` считать картой;
- любой `10/12-digit` считать ИНН;
- любой `dd.mm.yyyy` считать ПДн;
- любой `Иван Иванов` считать ФИО без контекста;
- CVV как любой `123`.

Лучшие инженерные решения:
- candidate -> normalize -> validate -> score confidence;
- хранить raw values только in-memory;
- для ambiguous entities использовать keyword windows и schema hints;
- иметь `unknown`/`low-confidence`, а не насильно подтверждать.

Что показать на защите:
- примеры near-miss, которые отфильтрованы;
- таблицу “regex-only vs validated pipeline”;
- precision-friendly design decisions.

## 2. Качество классификации — 25%

Что влияет:
- прозрачная формализация УЗ;
- приоритет спецкатегорий и биометрии;
- конфигурируемые thresholds;
- consistent per-file classification.

Что убивает:
- “магические” пороги без объяснения;
- непредсказуемость: одинаковые кейсы -> разные УЗ;
- смешение presence и volume без правил.

Лучшие решения:
- explicit rule precedence;
- separate counts for `occurrences`, `validated_occurrences`, `unique_hashes`, `rows_affected`;
- README с policy table.

Что показать:
- 4-5 файлов с разными УЗ и объяснение, почему именно так.

## 3. Производительность и масштабируемость — 20%

Что влияет:
- file-level parallelism;
- streaming/chunking for CSV/JSON/Parquet;
- OCR gating;
- bounded memory and incremental writes.

Что убивает:
- OCR всех изображений и PDF-страниц подряд;
- полная загрузка больших таблиц в память;
- single-thread run без аргументации;
- отсутствие timeouts.

Лучшие решения:
- process pool по файлам;
- chunk-based structured scanning;
- partial parse statuses;
- skip heuristics for huge images/video.

Что показать:
- `N files`, `X GB`, `Y files/sec`, `Z errors recovered`.
- Пояснить, где решение CPU-bound, а где IO-bound.

## 4. Качество отчета — 10%

Что влияет:
- читаемый per-file report;
- top risky files;
- counts by category;
- errors appendix;
- no raw PII.

Что убивает:
- dump в JSON без summary;
- сырые значения ПДн;
- отсутствие статуса валидации;
- невозможность понять, какие файлы реально опасны.

Лучшие решения:
- CSV summary + JSON detail + Markdown executive report;
- confidence/validation counts;
- privacy-safe masked previews only optionally.

Что показать:
- Markdown report как артефакт для жюри;
- один CSV row и один JSON record.

## 5. Техническая реализация — 5%

Что влияет:
- reproducible install;
- clean CLI;
- logs and errors;
- tests;
- docs.

Что убивает:
- fragile ad hoc script;
- hidden env dependencies без инструкции;
- падение на первом битом файле.

Что показать:
- `README`, `requirements.lock`, sample config, `pytest` output, synthetic benchmark.

---

# E. Architectural Options

| Вариант | Идея | Плюсы | Минусы | Риски | Сложность | Для хакатона |
|---|---|---|---|---|---|---|
| 1. Прагматичный MVP / fastest path | Один CLI, file-by-file processing, regex+validators, limited OCR | Максимально быстро собрать рабочее ядро | Слабее по OCR, DOC, MP4, advanced confidence | Может недобрать recall на сканах | Низкая | Хорош для 1-2 дней |
| 2. Balanced architecture | Модульный pipeline, extractor fallback chains, configurable rules, process pool, OCR auto | Лучший баланс score/риск/время | Чуть больше engineering overhead | Нужна дисциплина в scope | Средняя | Лучший выбор |
| 3. Ambitious / stronger but riskier | Пайплайн + OCR + NER/LLM second-pass + vector search/report UI | Может красиво смотреться и покрыть сложный текст | Очень легко утонуть, нестабильно, сложно дебажить | High FP, latency, demo risk | Высокая | Только если core уже готов |

## Рекомендация

Брать вариант 2.

Почему:
- Он дает достаточную глубину по реальным критериям.
- Позволяет показать сильную архитектуру без лишней хрупкости.
- Оставляет место для optional OCR/LLM, но не строит на них основу.

---

# F. Tech Stack Recommendation

## Shortlist

| Зона | Рекомендуемый стек | Зачем | Плюсы | Риски / ограничения | Fallback |
|---|---|---|---|---|---|
| Обход файлов | `pathlib`, `os.scandir` | быстрый walk | стандартная библиотека, без лишних зависимостей | MIME не определяет | `mimetypes` |
| Определение формата | `python-magic` optional | реальный mime/sniffing | спасает при неправильных extension | зависит от `libmagic` | extension + simple header sniff |
| CSV | `pandas.read_csv(chunksize=...)`, `csv` | chunked parse | удобно, быстро для MVP | кодировки и bad lines | `csv` + `charset-normalizer` |
| JSON | `orjson`, `ijson` | fast parse / streaming | большие JSON без полной загрузки | JSONL vs nested JSON | stdlib `json` |
| Parquet | `pyarrow` | columnar scan | лучший выбор для parquet | dependency heavier | `pandas` via `pyarrow` |
| XLS / XLSX | `pandas`, `xlrd`, `openpyxl` | spreadsheet parsing | единый API | старые `xls` tricky | `pyxlsb` if needed later |
| PDF | `pypdf`, `pdfplumber` | text extraction fallback chain | good balance | layout loss, scanned pdf no text | OCR on rendered pages |
| PDF render for OCR | `pypdfium2` | render page to image | fast enough, no external poppler required | adds complexity | skip PDF OCR in MVP |
| DOCX | `python-docx`, `docx2txt` | robust text extraction | reliable for common docs | misses complex layout sometimes | `mammoth` optional |
| DOC | `antiword` subprocess optional | legacy binary docs | practical if installed | system dependency | mark partial support / `textract` later |
| RTF | `striprtf` | text extraction | lightweight | formatting lost | none needed |
| HTML | `beautifulsoup4` + `lxml` | visible text extraction | reliable | noisy pages/scripts/styles | clean with tag stripping |
| Images | `Pillow` | image open/preprocess | standard | huge images memory | resize / skip threshold |
| OCR | `pytesseract` | OCR with rus+eng | strong if tesseract available | external binary, slower | `EasyOCR` only as optional backup |
| Video | `ffmpeg/ffprobe` or `opencv-python-headless` | frame sampling / subtitles | practical best-effort | high effort, low ROI | metadata-only + skip |
| CLI | `Typer` | good DX, typed options | readable CLI | extra dep | `argparse` |
| Logging | stdlib `logging` + optional `rich` | logs + console progress | stable, predictable | `rich` optional | pure logging |
| Config | `PyYAML` + `pydantic` optional | config-driven rules | explicit and reproducible | extra dep | dataclass + yaml |
| Reporting | `orjson`, `csv`, `jinja2`/manual md | outputs | simple and controllable | too much templating is waste | hand-written Markdown |
| Hashing / masking | stdlib `hashlib`, `hmac` | privacy-safe evidence | no extra deps | key management | salted SHA256 if HMAC not used |
| Concurrency | `concurrent.futures.ProcessPoolExecutor` | CPU-bound file jobs | simple | too many workers can thrash | sequential mode |
| Testing | `pytest`, `pytest-cov`, `hypothesis` optional | unit/integration | standard | property tests optional | pure pytest |

## Конкретная рекомендация по стеку

Для хакатона я бы взял:
- `Typer`
- `pandas`
- `pyarrow`
- `orjson`
- `ijson`
- `pypdf`
- `pdfplumber`
- `pypdfium2`
- `python-docx`
- `docx2txt`
- `striprtf`
- `beautifulsoup4`
- `lxml`
- `Pillow`
- `pytesseract`
- `PyYAML`
- `pytest`

Что не брать в ядро сразу:
- `spaCy`/`DeepPavlov`/тяжелые NLP-стеки;
- `unstructured` как silver bullet;
- web framework;
- vector DB.

---

# G. Detection Strategy

## Общий принцип

Правильный порядок:
1. Извлечь текст/табличные значения.
2. Нормализовать Unicode, пробелы, дефисы, separators.
3. Сгенерировать кандидатов.
4. Обогатить контекстом: колонка, строка, page number, соседние слова.
5. Провалидировать.
6. Присвоить confidence.
7. Агрегировать per-file без хранения сырого значения.

## Confidence model

- `high`: строгий валидатор + сильный контекст или structured field name.
- `medium`: format-valid candidate без сильного контекста.
- `low`: keyword/heuristic only.
- В УЗ engine лучше опираться на `high` и `medium`; `low` использовать осторожно.

## Обычные ПДн

| Сущность | Как искать | Снижение FP | Комментарий |
|---|---|---|---|
| ФИО | regex на 2-3 кириллических слова с заглавных букв; structured column names `фио`, `full_name`, `surname`, `name`, `patronymic`; формат `Иванов И.И.` | контекст `ФИО`, `сотрудник`, `пациент`, `получатель`; патронимические суффиксы `-вич`, `-вна`; исключать юрлица `ООО`, `АО`, `ИП` | без контекста очень шумно; лучше считать high only при context/schema support |
| Email | RFC-lite regex | lowercasing, reject obvious garbage, one `@`, valid TLD | high-confidence, одна из самых простых сущностей |
| Телефон | regex на `+7`, `8`, скобки/дефисы/пробелы; normalize to digits | требовать 10-11 цифр; исключать похожие банковские/паспортные паттерны; усиливать по keywords `тел`, `phone`, `моб.` | high при нормализации + длина + телефонные префиксы |
| Дата рождения | date regex + parsing | считать ПДн только при keywords `дата рождения`, `родился`, `DOB`, `birth`; reject impossible/future dates | дата сама по себе не ПДн-категория для детекции без контекста |
| Место рождения | phrase extraction после `место рождения`, `place of birth` | без ключевых слов не детектить | entity сложная, лучше context-driven |
| Адрес проживания/регистрации | keywords `адрес`, `регистрации`, `проживания`, `место жительства`; дальше шаблоны `г.`, `ул.`, `д.`, `кв.`, `просп.`, `обл.` | не детектить голый адрес без address markers; использовать словарь типов улиц и регионов | высокий риск FP, особенно в HTML/общих текстах |

## Государственные идентификаторы

| Сущность | Как искать | Validation / контекст | Снижение FP |
|---|---|---|---|
| Паспорт РФ | regex на `NN NN NNNNNN`, слитный и spaced форматы | keywords `паспорт`, `серия`, `номер`, `код подразделения`, `выдан`; plausible series/year checks optional | без контекста не считать high-confidence |
| СНИЛС | regex `XXX-XXX-XXX YY` и 11 digits слитно | checksum обязателен | очень сильный high-confidence candidate |
| ИНН физлица / юрлица | 12 и 10 digits | checksum обязателен; keywords `ИНН`, column name boosts confidence | без checksum не засчитывать как confirmed |
| Водительское удостоверение | digits/series-number patterns + keywords `водительское`, `ВУ`, `вод. удостоверение`, `driver license` | строгая валидация слабая; использовать format + context + nearby dates/categories | без контекста почти не детектить |
| MRZ | строки из `A-Z0-9<` фиксированной длины, 2-3 lines | ICAO check digits where applicable; transliteration-like pattern | один из лучших high-precision паттернов при полном совпадении |

## Платежная информация

| Сущность | Как искать | Validation / контекст | Снижение FP |
|---|---|---|---|
| Банковская карта | regex на 13-19 digits с пробелами/дефисами | Luhn обязателен; issuer prefix optional; keywords `карта`, `VISA`, `MC`, `МИР`, `PAN` повышают confidence | исключать телефоны, счета, SNILS-like values |
| Банковский счет | 20 digits | лучше подтверждать вместе с БИК и keywords `р/с`, `счет`, `account` | standalone 20-digit очень шумный |
| БИК | 9 digits | базовые checks + keywords `БИК`, `банк`, `bank identifier` | standalone 9-digit без контекста шумный |
| Пара БИК + счет | искать в одной строке/ячейке/блоке | применять checksum/account control logic | это сильный сигнал для payment detection |
| CVV/CVC | только keywords `cvv`, `cvc`, `cvv2`, `security code` рядом + 3/4 digits | без card context считать очень осторожно | standalone detection почти бесполезна и шумна |

## Биометрия

| Сущность | Как искать | Снижение FP |
|---|---|---|
| Упоминания биометрии | словарь: `биометр`, `отпечаток пальца`, `дактилоскоп`, `радужная оболочка`, `скан лица`, `face embedding`, `голосовой слепок`, `биометрический шаблон` | lemmatization optional; учитывать negation window `без биометрии`, `не содержит биометрические данные` |

## Специальные категории ПДн

| Категория | Как искать | Снижение FP |
|---|---|---|
| Национальность / этничность / раса | keywords `национальность`, `этническая принадлежность`, `раса`, конкретные этнонимы | требовать person-centric context или field label |
| Политические взгляды | `политические взгляды`, `партийная принадлежность`, `убеждения`, названия партий рядом с персоной | generic news text без person context лучше считать low |
| Религиозные / философские убеждения | `религия`, `вероисповедание`, `атеист`, `православный`, `мусульманин` и т.д. | нужен context around personal data form/profile |
| Состояние здоровья | `диагноз`, `анамнез`, `аллергия`, `инвалидность`, `болеет`, `ВИЧ`, `беременность`, `медицинское заключение` | generic медицинские статьи могут шуметь; лучше person-centric clues |
| Интимная жизнь | `сексуальная ориентация`, `интимная жизнь` и близкие формулировки | держать очень строгий словарь и контекст |
| Иные спецкатегории по 152-ФЗ | curated lexicon + manual review list | только high-signal phrases |

## Где нужен strict validation

- Банковские карты.
- СНИЛС.
- ИНН.
- MRZ checksums.
- Date parsing for birth dates.
- БИК+счет, если пара найдена.

## Где нужна heuristic detection

- ФИО.
- Адреса.
- Паспорт РФ.
- Водительское удостоверение.
- Биометрия и спецкатегории.

## Где полезен словарь

- Типы улиц и адресные маркеры.
- Биометрические термины.
- Спецкатегории ПДн.
- Контекстные ключевые слова для форм и колонок.

## Где полезны contextual clues

- Для любой сущности, которую трудно валидировать математически.
- В structured data: название колонки, sheet name, JSON key path.
- В documents: words in ±50 chars window, same line, same paragraph.

---

# H. Validation Strategy

## Что валидировать обязательно

| Сущность | Валидация |
|---|---|
| Банковская карта | алгоритм Луна |
| СНИЛС | checksum согласно правилам контрольного числа |
| ИНН 10/12 | checksum |
| Date of birth | parse + not in future + plausible age range |
| Email | syntax-lite |
| Phone | normalized length/prefix sanity |
| MRZ | ICAO checksums for parsed fields |

## Что валидировать желательно

| Сущность | Валидация |
|---|---|
| БИК | 9 digits + допустимые ограничения |
| Банковский счет | если рядом есть БИК, применить checksum/control logic |
| Паспорт РФ | формат + context + plausible series/issue markers |
| Водительское удостоверение | формат + context only |
| Адрес | структурные маркеры, не математическая валидация |

## Что нельзя надежно валидировать без контекста

- ФИО.
- Адреса.
- Биометрические упоминания.
- Спецкатегории ПДн.
- Место рождения.
- Старые/вариативные номера водительских удостоверений.

## Как валидация снижает false positive

- Убирает случайные числовые последовательности.
- Отделяет реальные финансовые/гос ID от мусора в логах, таблицах, HTML.
- Позволяет считать в УЗ только `confirmed` или `high-confidence` случаи.

## Практический принцип

Для каждой детекции хранить:
- `candidate_detected: bool`
- `validation_status: valid | invalid | unknown`
- `confidence: high | medium | low`
- `validation_reason`

В репортах показывать counts по всем 3 измерениям.

---

# I. UZ Classification Logic

## Проблема

ТЗ задает классы УЗ, но не задает четких количественных thresholds. Это надо формализовать и вынести в config.

## Рекомендуемая модель агрегации

Для каждого файла считать:
- `occurrences_total_by_category`
- `validated_occurrences_by_category`
- `unique_hashes_by_category`
- `rows_or_blocks_affected_by_category`
- `families_present`: `ordinary`, `government`, `payment`, `biometric`, `special`

## Рекомендуемые family thresholds по умолчанию

```yaml
uz_thresholds:
  ordinary_large_unique: 20
  ordinary_large_occurrences: 100
  ordinary_large_rows: 50

  government_large_unique: 5
  government_large_occurrences: 20
  government_large_rows: 10

  payment_large_unique: 3
  payment_large_occurrences: 5
  payment_large_rows: 3
```

Это не “истина”, а defensible default. Без датасета thresholds должны быть конфигурируемыми.

## Формализованный rules engine

```text
If special_present or biometric_present:
    UZ-1

Else if validated_payment_present:
    UZ-2

Else if government_large_volume:
    UZ-2

Else if government_present:
    UZ-3

Else if ordinary_large_volume:
    UZ-3

Else if ordinary_present:
    UZ-4

Else:
    no_pdn / null
```

## Что считать `present`

- Для government/payment лучше опираться на `validated` или `high-confidence`.
- Для special/biometric допустимо `medium/high-confidence` lexical detection.
- Для ordinary можно использовать `medium/high-confidence`.

## Как избегать спорных кейсов

- Не повышать УЗ из-за `low-confidence` alone.
- Не считать generic article про здоровье автоматически УЗ-1 без person-centric evidence, если это не профиль/реестр/анкета.
- Для structured datasets дополнительно использовать `rows_affected`, а не только raw count.
- Держать `classification_explanation`: какие правила сработали.

## Что писать в отчете

Для каждого файла:
- `assigned_uz`
- `uz_reason_codes`: например `SPECIAL_CATEGORY_PRESENT`, `VALIDATED_CARD_PRESENT`, `ORDINARY_LARGE_VOLUME`

---

# J. Privacy-Safe Reporting

## Принципы

- Не сохранять сырые значения ПДн в output.
- Максимум 1-2 masked previews на категорию только по explicit flag.
- Для корреляции повторов использовать `HMAC-SHA256(normalized_value, secret)`.
- В логах не печатать full matches.

## Что хранить вместо значений

- `value_hash_short`: первые 12-16 hex символов HMAC.
- `masked_preview`: опционально.
- `validation_status`
- `confidence`
- `location_hint`: page/row/column, без сырого контента.

## Маскирование

| Сущность | Маскирование |
|---|---|
| Email | `i***@d***.ru` |
| Phone | `+7*******12` |
| Card | `**** **** **** 1234` |
| Паспорт | `45 0* ******` |
| SNILS | `***-***-*** 12` |
| ИНН | `**********12` |
| Адрес | лучше не показывать sample вообще |
| ФИО | лучше не показывать sample вообще |

## CSV report

Лучший формат:
- одна строка на файл;
- только summary fields.

Рекомендуемые поля:
- `file_path`
- `file_format`
- `file_size_bytes`
- `scan_status`
- `uz`
- `ordinary_count`
- `government_count`
- `payment_count`
- `biometric_count`
- `special_count`
- `validated_count_total`
- `high_confidence_count_total`
- `errors_count`
- `classification_reasons`

## JSON report

Использовать как основной detail output.

Структура:
- `run_metadata`
- `summary`
- `files[]`
- `errors[]`

Для `files[]`:
- file metadata
- extraction status
- counts by category/family
- `assigned_uz`
- `classification_explanation`
- `detections_summary[]` with `category`, `count`, `validated_count`, `confidence_breakdown`, `sample_hashes`

## Markdown report

Должен быть human-friendly:
- overall totals
- files scanned / failed / partial
- distribution by format
- distribution by UZ
- top-10 risky files
- counts by category
- appendix with parser errors

Это лучший artifact для жюри.

## Хранить ли sample values

Рекомендация:
- default: нет.
- optional debug mode: masked only.
- сырые значения не писать вообще ни в какой output.

---

# K. Project Structure

```text
samshack/
  README.md
  pyproject.toml
  configs/
    default.yaml
    fast.yaml
    ocr.yaml
  src/
    pdn_scanner/
      __init__.py
      cli.py
      config.py
      enums.py
      models.py

      scanner/
        walker.py
        format_detector.py
        dispatcher.py

      extractors/
        base.py
        structured.py
        pdf.py
        office.py
        html.py
        image.py
        video.py
        utils.py

      normalize/
        text.py
        values.py
        context.py

      detectors/
        ordinary.py
        government.py
        payment.py
        sensitive.py
        engine.py

      validators/
        cards.py
        snils.py
        inn.py
        bank.py
        mrz.py
        dates.py
        common.py

      classify/
        uz_engine.py
        thresholds.py

      reporting/
        csv_reporter.py
        json_reporter.py
        markdown_reporter.py
        masking.py

      runtime/
        logging_setup.py
        errors.py
        workers.py
        metrics.py
        timeouts.py

      synth/
        generator.py
        ground_truth.py

  tests/
    unit/
    integration/
    e2e/
    fixtures/

  docs/
    architecture.md
    detection_rules.md
    demo_plan.md
```

## Назначение модулей

- `cli.py`: entrypoint и subcommands.
- `config.py`: загрузка YAML, thresholds, feature flags.
- `models.py`: internal schemas/dataclasses.
- `scanner/*`: walk, mime/extension detection, routing.
- `extractors/*`: per-format parsing.
- `normalize/*`: cleanup text, canonicalization.
- `detectors/*`: category-specific candidate generation.
- `validators/*`: strict checks.
- `classify/*`: UZ assignment.
- `reporting/*`: output generation and masking.
- `runtime/*`: logs, worker pool, metrics, resilience.
- `synth/*`: synthetic dataset + ground truth manifest.

---

# L. Data Models

## Рекомендуемые внутренние модели

```python
@dataclass
class FileDescriptor:
    path: str
    rel_path: str
    size_bytes: int
    extension: str
    mime_type: str | None
    detected_format: str
    file_hash: str | None

@dataclass
class ExtractedContent:
    file_path: str
    status: str  # ok | partial | unsupported | error | timeout
    text_chunks: list[str]
    structured_rows_scanned: int
    pages_scanned: int | None
    sheets_scanned: int | None
    warnings: list[str]

@dataclass
class DetectionResult:
    category: str
    family: str
    detector_id: str
    confidence: str  # high | medium | low
    validation_status: str  # valid | invalid | unknown
    value_hash: str
    masked_preview: str | None
    occurrences: int
    locations: list[str]
    context_keywords: list[str]

@dataclass
class FileScanResult:
    file: FileDescriptor
    extraction: ExtractedContent
    detections: list[DetectionResult]
    counts_by_category: dict[str, int]
    counts_by_family: dict[str, int]
    assigned_uz: str | None
    classification_reasons: list[str]
    processing_errors: list[str]
    duration_ms: int

@dataclass
class ProcessingError:
    file_path: str
    stage: str
    error_code: str
    message: str
    recoverable: bool

@dataclass
class RunSummary:
    started_at: str
    finished_at: str
    files_total: int
    files_processed: int
    files_partial: int
    files_failed: int
    unsupported_files: int
    by_format: dict[str, int]
    by_uz: dict[str, int]
    by_category: dict[str, int]
    total_duration_sec: float
```

## Ключевой принцип модели

- Raw detected value может существовать transiently in-memory до masking/hash.
- В persisted report raw value быть не должно.

---

# M. CLI / UX Design

## Команды

```bash
pdn-scan scan /data --out ./out
pdn-scan scan /data --out ./out --config configs/ocr.yaml --ocr auto --workers 6
pdn-scan synth generate ./synthetic --profile baseline
pdn-scan validate-config configs/default.yaml
```

## Основные флаги

- `--out PATH`  
  директория output artifacts
- `--config PATH`  
  YAML config
- `--workers N`  
  число worker processes
- `--ocr off|auto|force`  
  режим OCR
- `--ocr-lang rus+eng`
- `--max-file-size-mb N`
- `--timeout-sec N`
- `--formats csv,json,md`
- `--log-level DEBUG|INFO|WARN|ERROR`
- `--fail-fast`
- `--continue-on-error`
- `--include-masked-samples`
- `--hash-secret-env VAR_NAME`
- `--skip-video`
- `--skip-ocr-on-pdf`
- `--csv-chunk-size N`
- `--parquet-row-group-limit N`

## UX принципы

- По умолчанию `continue-on-error`.
- По умолчанию `ocr=auto`, не `force`.
- В stdout печатать progress и summary.
- Детали ошибок складывать в файл.
- После завершения печатать пути к `summary.csv`, `report.json`, `report.md`.

---

# N. Error Handling / Robustness

| Проблема | Стратегия |
|---|---|
| Битый файл | пометить `status=error`, записать ошибку, продолжить |
| Неподдерживаемый формат | `status=unsupported`, лог + continue |
| Огромный файл | size threshold, chunked parsing, timeout |
| Unknown encoding | `charset-normalizer`, fallback to `utf-8`/`cp1251`/`latin1` with replacement |
| OCR failure | warning + continue without OCR result |
| Corrupted PDF | fallback extractor chain, потом partial/error |
| Corrupted DOC | best-effort parser, иначе partial/unsupported |
| Partially parsed file | сохранить partial status и то, что удалось извлечь |
| Timeout на одном файле | per-file timeout, continue |
| Too many detections | cap sample hashes, aggregate counts only |
| Parser memory pressure | sequential fallback for huge files, chunking |

## Обязательные принципы robustness

- Ни один файл не должен валить run.
- Каждый file result должен иметь status.
- Ошибки нужны и в логах, и в JSON summary.
- Partial extraction лучше, чем hard fail.

---

# O. Performance / Scalability

## Главные bottlenecks

- OCR.
- PDF parsing.
- Image decode / preprocessing.
- Large CSV/XLS reads.
- Regex over huge text blobs.
- Legacy office format extraction.

## Что делать в MVP

- File-level `ProcessPoolExecutor`.
- Chunked CSV scanning.
- Parquet scanning через `pyarrow`.
- PDF extractor chain без OCR по умолчанию.
- OCR только:
  - image files;
  - scanned PDF pages, если на странице почти нет extractable text.
- Incremental write в JSONL/internal results.
- Не держать весь corpus в памяти.

## Где multiprocessing нужен

- OCR.
- PDF/image-heavy files.
- CPU-heavy regex on large text.
- Possibly DOC parsing.

## Где sequential достаточно

- Directory walk.
- Small HTML/JSON/text files.
- Final report aggregation.

## Как не сожрать память

- Structured files читать чанками.
- Не собирать все text chunks всех файлов в один список.
- Сохранять только агрегаты и ограниченный set hash values.
- Limit sample hashes per category, например до 10 на файл.

## Большие structured files

Рекомендация:
- `CSV`: chunksize 5k-20k rows.
- `Parquet`: row group iteration or batched read.
- `XLS`: per-sheet scan, без загрузки всех листов сразу если возможно.
- Колонки с именами-сигналами можно сканировать приоритетно.

## OCR-оптимизация

- `ocr=auto`:
  - для изображений меньше минимального размера OCR не делать;
  - для огромных изображений сначала resize/grayscale;
  - для PDF OCR только if extracted_text_len < threshold.
- Ограничивать max pages per file для OCR-config.
- Tesseract language pack `rus+eng`.

## Что избыточно для хакатона

- Spark/Dask.
- GPU OCR pipeline.
- Distributed queue.
- Persistent job DB.
- Microservices.

---

# P. Synthetic Dataset / Test Plan

## 1. Как создать synthetic dataset

Сделать генератор с manifest ground truth:
- использовать `Faker("ru_RU")`;
- генерировать валидные ПДн и near-miss невалидные;
- сериализовать в разные форматы;
- для каждого файла писать `ground_truth.json` с категориями и counts.

## 2. Что положить в synthetic dataset

| Тип | Что должно быть |
|---|---|
| CSV | маленькие и большие таблицы, разные кодировки, колонки `ФИО`, `email`, `ИНН`, `СНИЛС`, `адрес` |
| JSON | nested objects, arrays, JSONL |
| Parquet | большие row groups, mixed schema |
| PDF | digital text docs, forms, scans |
| DOCX | анкеты, договоры, кадровые документы |
| DOC | legacy документы с текстом |
| RTF | простые текстовые карточки |
| XLS/XLSX | payroll-like sheets, multiple tabs |
| HTML | forms, profile pages, tables |
| JPEG/PNG/TIF/GIF | scanned forms, passport snippets, card screenshots |
| MP4 | видео с оверлеями текста или субтитрами |
| Broken files | corrupted pdf/doc/json/csv |

## 3. Какие valid/invalid кейсы нужны

### Valid cases

- Валидные карты, СНИЛС, ИНН.
- Паспорт в нескольких форматах записи.
- ФИО с отчеством, без отчества, с инициалами.
- Телефоны с `+7`, `8`, пробелами, скобками.
- Адреса с разными сокращениями.
- MRZ.
- Медицинские формулировки и биометрические упоминания.
- БИК + счет в одной строке.

### Invalid / near-miss cases

- 16-digit, не проходящие Лун.
- 10/12-digit, не проходящие checksum ИНН.
- 11-digit, похожие на СНИЛС, но с неверной контрольной суммой.
- Даты без birth context.
- Телефоно-подобные номера заказов.
- Имена компаний, похожие на ФИО.
- Адреса организаций, не относящиеся к физлицам.
- Generic article about religion/health without personal record.
- `CVV 123` в примере документации, а не платежных данных.

## 4. Как тестировать FP / FN

- Для каждого файла иметь ground truth по категориям.
- Считать per-category precision/recall.
- Отдельно считать precision на risk-heavy entities:
  - card
  - SNILS
  - INN
  - passport
  - special categories
- Иметь “noise-only” corpus без ПДн.

## 5. Unit / Integration / E2E tests

### Unit

- `luhn_validator`
- `snils_validator`
- `inn_10_validator`
- `inn_12_validator`
- `mrz_checksum`
- `phone_normalizer`
- `date_of_birth_context`
- `masking_functions`
- `uz_rule_engine`

### Integration

- `CSV -> detector -> validator`
- `PDF -> extractor -> detector`
- `HTML -> cleaner -> detector`
- `OCR image -> detector`
- `error path on corrupted pdf`
- `partial parse on malformed csv`

### E2E

- scan small mixed dataset
- generate all 3 output formats
- confirm no raw PII in outputs
- confirm UZ assignments on reference files
- confirm continue-on-error behavior

## Минимальный synthetic benchmark suite

- `precision_set`: mostly near-miss/noise
- `recall_set`: valid entities across formats
- `ocr_set`: scanned images/pdfs
- `robustness_set`: broken/huge files
- `classification_set`: files for UZ-1/2/3/4

---

# Q. MVP Plan

## MVP v1

- Recursive scan.
- Format detection by extension + optional MIME.
- Extractors:
  - CSV
  - JSON
  - Parquet
  - PDF
  - DOCX
  - RTF
  - XLS
  - HTML
  - JPEG/PNG/TIF/GIF with optional OCR
- Best-effort DOC support.
- MP4 as best-effort metadata/frame-sampling stub.
- Detectors for all required entity families.
- Validators for card/SNILS/INN/date/MRZ/bank/date.
- UZ rules engine.
- CSV + JSON + Markdown reports.
- Masking/HMAC.
- Continue-on-error.
- Basic process pool.
- Basic test suite.

## v2

- OCR auto-mode on scanned PDFs.
- Better DOC fallback chain.
- Better structured-data schema hints.
- Better address/FIO heuristics.
- Confidence scoring refinement.
- Synthetic dataset generator and benchmark script.
- More detailed Markdown visuals.

## Stretch goals

- Cross-file entity correlation via hashed identities.
- Optional local NER for FIO/address disambiguation.
- Optional local LLM second-pass only for special-category ambiguity.
- Simple analyst dashboard.

## Что точно не надо делать вначале

- Полноценный web UI.
- RAG по сырому корпусу.
- LLM-first detection.
- Distributed architecture.
- OCR every page/frame by default.
- “Умный” self-learning classifier без baseline.

---

# R. Implementation Roadmap

| Этап | Цель | Deliverables | Зависимости | Риски | Критерий готовности |
|---|---|---|---|---|---|
| 0 | Formalize scope | architecture note, category matrix, thresholds config draft | none | scope creep | команда согласовала MVP |
| 1 | Skeleton | repo, CLI, config, models, logging | 0 | churn in interfaces | `scan` command запускается |
| 2 | Scanner + format detection | walker, dispatcher, format enum | 1 | wrong routing | mixed directory scan works |
| 3 | Core extractors | CSV/JSON/Parquet/PDF/DOCX/RTF/XLS/HTML | 2 | parser failures | extractor tests green |
| 4 | Normalization + detectors | entity detectors + context hints | 3 | FP explosion | categories detected on fixtures |
| 5 | Validators | Luhn/SNILS/INN/MRZ/bank/date | 4 | checksum bugs | validators unit-tested |
| 6 | UZ engine + reporting | rules engine, CSV/JSON/MD outputs | 4,5 | unclear thresholds | classification fixtures green |
| 7 | Robustness + performance | process pool, timeouts, error handling, chunking | 3-6 | race conditions, memory | run survives broken corpus |
| 8 | OCR + best-effort legacy/video | image OCR, scanned PDF OCR auto, DOC/MP4 fallback | 3-7 | time sink | only if core stable |
| 9 | Synthetic dataset + benchmark | generator, ground truth, demo datasets | 3-8 | overinvestment | measurable precision/recall |
| 10 | Demo hardening | sample configs, README, demo script | all | demo surprises | one-command demo works |

## Правильный порядок

Сначала:
- extractor coverage на core formats;
- validators;
- UZ logic;
- report quality.

Потом:
- OCR;
- performance tuning;
- legacy/video polish.

---

# S. Team Split

## Команда из 2 человек

**Человек 1**
- scanner
- format detection
- extractors
- concurrency/performance

**Человек 2**
- detectors
- validators
- UZ engine
- reporting
- tests/demo

Синк:
- общий `models.py` и `config.yaml` контракт в первый час.

## Команда из 3 человек

**Человек 1**
- scanner + extractors structured/doc/html

**Человек 2**
- detectors + validators + normalization

**Человек 3**
- reporting + CLI + robustness + tests + demo

## Команда из 4 человек

**Человек 1**
- core pipeline + scanner + workers

**Человек 2**
- extractors + OCR + legacy formats

**Человек 3**
- detectors + validators + UZ logic

**Человек 4**
- synthetic dataset + tests + reporting + demo assets + README

## Важное организационное правило

- Один человек должен быть technical integrator/architect.
- Не распараллеливать без согласованного data model и config schema.

---

# T. Demo / Pitch Strategy

## Что показывать

1. CLI запуск на mixed dataset.
2. Progress + graceful handling of bad files.
3. Markdown summary.
4. Один JSON detail record.
5. Топ risky files с УЗ.
6. Пример, где validator убрал false positive.
7. Пример scanned image/PDF, если OCR успели стабилизировать.

## Лучший demo flow

1. Показать directory с разными форматами.
2. Запустить `pdn-scan scan ./demo-data --out ./demo-out --ocr auto`.
3. После завершения открыть `report.md`.
4. Показать:
   - распределение УЗ;
   - top risky files;
   - category totals;
   - errors recovered.
5. Показать один файл `UZ-1`, один `UZ-2`, один `UZ-4`.
6. Показать, что в outputs нет raw PII.
7. Показать comparison: regex-only noisy case vs validated output.

## Какие цифры показать

- `files scanned`
- `GB processed`
- `processing time`
- `files/sec`
- `errors recovered`
- `precision on synthetic benchmark`
- `false positives filtered by validators`

## Как объяснить точность

- “Мы не ищем все подряд regex-ом.”
- “Для numerically structured identifiers у нас deterministic validators.”
- “Для ambiguous text используем context scoring и schema hints.”
- “Low-confidence signals не повышают УЗ автоматически.”

## Как продать privacy-safe подход

- “Система фиксирует факт наличия ПДн без публикации значений.”
- “Используем masking/HMAC, поэтому одинаковые сущности можно коррелировать без раскрытия.”
- “Это важнее для enterprise readiness, чем красивые raw examples.”

## Как объяснить УЗ

- Показать одну таблицу rule precedence.
- Показать configurable thresholds.
- Подчеркнуть explainability.

## Как показать производительность без вранья

- Дать честный benchmark на вашем synthetic/demo corpus.
- Не обещать distributed scale.
- Ясно сказать: OCR auto-mode selective; full OCR на все файлы сознательно не включен.

---

# U. What Not To Do

- Не строить core detection на LLM.
- Не хранить сырые ПДн в отчетах, логах, debug prints.
- Не делать UI раньше extractor/validator/UZ engine.
- Не OCR-ить все подряд.
- Не считать любую дату ПДн.
- Не считать любой capitalized 2-word phrase ФИО.
- Не считать любой 16-digit номер банковской картой.
- Не пытаться “идеально” решить адреса и ФИО раньше жестко валидируемых сущностей.
- Не тратить полдня на MP4, пока не закрыты PDF/CSV/JSON/DOCX.
- Не захардкодить thresholds без config.
- Не падать на первом битом файле.
- Не писать output, который невозможно быстро объяснить жюри.
- Не тащить тяжелые NLP/ML зависимости без измеримой пользы.
- Не смешивать extraction quality и classification logic в одну непрозрачную кашу.

---

# V. Open Questions / Ambiguities

## Что не определено явно

- Как именно организаторы трактуют “большой объем”.
- Требуется ли per-file УЗ только, или еще overall dataset УЗ.
- Насколько обязательна реальная поддержка `DOC` и `MP4`.
- Есть ли в датасете `XLSX`, хотя в ТЗ указан `XLS`.
- Насколько много scanned PDFs / image-only docs.
- Русский-only corpus или mixed ru/en.

## Что стоит уточнить у организаторов

- Можно ли использовать внешние бинарные зависимости: `tesseract`, `antiword`, `ffmpeg`.
- Требуется ли обрабатывать вложенные архивы.
- Нужен ли учет embedded images in PDF/DOCX.
- Ожидается ли оценка по полноте OCR.
- Какие именно форматы отчетов обязательны в защите.

## Что сделать конфигурируемым

- thresholds for UZ.
- OCR mode.
- per-file timeout.
- max file size.
- allowed/blocked formats.
- masked sample policy.
- worker count.
- validation strictness for ambiguous entities.

## Где без реального датасета неопределенность максимальна

- ROI OCR.
- Need for DOC binary depth.
- Address detection aggressiveness.
- Special-category detection precision.
- Value of MP4 support.

---

# W. Final Recommendation

## 1. Итоговый рекомендуемый подход

Строить не “AI-решение”, а explainable data scanning pipeline:
- robust extraction;
- rule-based detection;
- deterministic validators;
- configurable UZ rules;
- privacy-safe reporting;
- selective OCR.

## 2. Рекомендуемая архитектура

Balanced modular pipeline:
- scanner
- format detector
- extractor chain
- normalization
- detectors
- validators
- UZ engine
- reporters
- runtime/performance layer

Это лучший компромисс между score, устойчивостью и сроком.

## 3. Рекомендуемый стек

- `Typer`
- `pandas`
- `pyarrow`
- `orjson`
- `ijson`
- `pypdf`
- `pdfplumber`
- `pypdfium2`
- `python-docx`
- `docx2txt`
- `striprtf`
- `beautifulsoup4` + `lxml`
- `Pillow`
- `pytesseract`
- `PyYAML`
- `pytest`

## 4. Рекомендуемый MVP

Сначала закрыть:
- CSV/JSON/Parquet/PDF/DOCX/RTF/XLS/HTML extractors
- image OCR optional
- strict validators
- UZ rule engine
- CSV/JSON/Markdown reports
- continue-on-error
- chunking + process pool
- synthetic benchmark mini-suite

DOC binary и MP4 сделать best-effort, не core.

## 5. Топ-5 вещей, которые дадут максимум шансов на высокий результат

- Сильные validators + context-aware heuristics для снижения false positive.
- Четкий explainable rules engine для УЗ с config thresholds.
- Privacy-safe отчеты без raw PII, но с достаточной аналитической полезностью.
- Robust extraction pipeline с fallback и partial/error statuses.
- Selective OCR и честная performance story вместо “магии”.

## Что делать первым же делом

1. Зафиксировать data model, config schema и category matrix.
2. Собрать scanner + core extractors.
3. Реализовать validators.
4. Собрать per-file aggregation и UZ engine.
5. Сделать synthetic fixtures и benchmark для быстрого измерения качества.

## Что я бы не делал до готовности core

- LLM/RAG.
- UI.
- advanced NLP.
- distributed scaling.
- глубокую обработку MP4.

## Про LLM / RAG, если все же пробовать

- В core pipeline они не нужны.
- Допустимое место: second-pass для ambiguous special-category snippets или генерация narrative summary по уже безопасному JSON report.
- Лучше использовать локальную русскоязычную/multilingual instruct-модель 7B-14B класса, если она уже доступна, а не строить на облаке.
- RAG имеет смысл только поверх safe aggregated report/metadata, а не поверх сырых документов.
- До готового baseline их подключать не стоит: риск для privacy, reproducibility и deadline выше потенциальной пользы.
