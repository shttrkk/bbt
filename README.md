# PDN Scanner

CLI-проект для локального поиска персональных данных в смешанном файловом хранилище. Архитектура следует baseline из `HACKATHON_PDN_ANALYSIS.md` и `HACKATHON_SOLUTION_PLAN.md`: `scan -> detect format -> dispatch extractor -> normalize -> detect -> validate -> aggregate -> classify(UZ) -> report`.

Текущий статус: `v0.1.0`

## Что делает CLI

- Рекурсивно обходит директорию.
- Определяет формат файла по extension и, при наличии, по MIME.
- Маршрутизирует файл в extractor.
- Нормализует текст и извлеченные значения.
- Ищет baseline-кандидаты ПДн rule-based способом.
- Валидирует `bank card`, `СНИЛС`, `ИНН`.
- Классифицирует файл по `УЗ-1..УЗ-4` или `NO_PDN`.
- Генерирует privacy-safe отчеты `CSV`, `JSON`, `Markdown`.
- Продолжает выполнение при ошибках чтения и неподдерживаемых файлах.

## Статус версии

`v0.1.0` закрывает стартовый локальный каркас:

- Рабочий CLI `pdn-scan`.
- Рабочие extractors: `txt`, `csv`, `json`, `html`.
- Stub extractors: `pdf`, `docx`, `rtf`, `xls/xlsx`, `parquet`, `image`, `doc`, `mp4`.
- Baseline detectors: `email`, `phone`, `person_name`, `address`, `bank card candidate`, `SNILS`, `INN`.
- Валидаторы: `Luhn`, `СНИЛС`, `ИНН`.
- Explainable UZ classification.
- Privacy-safe reporting без сохранения raw PII.

## Форматы

Готово в `v0.1.0`:

- `TXT`
- `CSV`
- `JSON`
- `HTML`

Stub / partial:

- `PDF`
- `DOCX`
- `RTF`
- `XLS/XLSX`
- `Parquet`
- `Images`
- `DOC`
- `MP4`

## Локальный запуск через venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Команды CLI

Проверка версии:

```bash
pdn-scan version
```

Проверка YAML-конфига:

```bash
pdn-scan validate-config configs/default.yaml
```

Запуск сканирования:

```bash
pdn-scan scan ./share --out ./artifacts --config configs/default.yaml
```

## Выходные артефакты

CLI создает:

- `summary.csv` — per-file summary;
- `report.json` — структурированный run report;
- `report.md` — краткая executive summary;

Артефакты не сохраняют сырые ПДн. В отчет попадают только:

- counts по категориям и семействам;
- `validation_status`;
- `confidence`;
- `masked_preview` при включенном флаге;
- короткие hashes;
- объяснение `UZ` classification.

## Конфиги

- `configs/default.yaml` — baseline профиль для локальной разработки.
- `configs/fast.yaml` — легкий профиль без OCR и без дорогих шагов.
- `configs/ocr.yaml` — профиль под selective OCR для следующих итераций.

## Тесты

```bash
pytest
```

Покрыты:

- `Luhn`
- `СНИЛС`
- `ИНН`
- CLI smoke flow

## Документация

- [docs/architecture.md](docs/architecture.md)
- [docs/roadmap.md](docs/roadmap.md)
- [status/IMPLEMENTATION_STATUS.md](status/IMPLEMENTATION_STATUS.md)

## Ограничения текущего этапа

- OCR не включен в core pipeline по умолчанию.
- `DOC`, `MP4`, legacy/scan-heavy потоки пока только как hooks.
- Anti-false-positive слой для шаблонов и public policy docs пока базовый.
- Structured scanning пока без chunked parquet/Excel implementation.
