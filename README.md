# PDN Scanner

`pdn-scanner` — локальный CLI-проект для поиска рискованного и необоснованного хранения персональных данных в смешанном файловом хранилище.

Финальная рамка проекта:
- цель не в том, чтобы найти любые ПДн
- цель в том, чтобы выделить файлы, похожие на утечку или на unjustified storage
- публичные, служебно оправданные и шаблонные документы не должны автоматически становиться positive

Главный финальный артефакт репозитория: [result.csv](/Users/shttrkk/Downloads/ПДнDataset/result.csv).

Подробное описание финальной поставки: [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md).

## Финальное состояние

- версия проекта: `0.1.1`
- основной запуск: `pdn-scan scan`
- поддерживаемые форматы в коде: `txt`, `csv`, `json`, `parquet`, `pdf`, `docx`, `rtf`, `xls/xlsx`, `html`, `image`, `doc`
- OCR-ветка есть и запускается отдельными конфигами
- итоговый конкурсный `result.csv` в этом репозитории зафиксирован вручную и не должен меняться

## Что делает система

Pipeline:

`scan -> detect format -> dispatch extractor -> detect -> quality-layer -> leak-context -> UZ classify -> report`

Основные этапы:

1. Обход каталога и построение `FileDescriptor`
2. Определение формата по extension и MIME
3. Извлечение текста и структуры из файла
4. Детекция ordinary / government / payment / special / biometric сигналов
5. Quality-layer:
   template suppression
   public-doc suppression
   reference-data suppression
   HTML noise suppression
   structured noise suppression
   office/pdf/image format-specific gating
6. Leak-aware оценка контекста хранения:
   genre
   risk score
   justification score
   noise score
   storage class
7. Explainable классификация в `UZ-1..UZ-4` или `NO_PDN`
8. Privacy-safe отчёты без raw PII

## Leak-Aware интерпретация

Система делит файлы на 3 смысловых класса:

- `TARGET_LEAK`
  личные формы, анкеты, доверенности, consent-документы, внутренние employee docs, correspondence, subject-level exports, изображения личных документов
- `PD_BUT_JUSTIFIED_STORAGE`
  публичные staff contacts, official contact docs, public reports, justified corporate/public disclosures
- `NON_TARGET`
  шаблоны, политики, инструкции, орг-реквизиты, narrative noise, reference-like данные без subject context

Positive в submission определяется не по факту наличия ПДн, а по сочетанию:
- жанра документа
- связки персональных якорей
- чувствительности
- контекста хранения
- отсутствия разумного business/public justification

## Структура репозитория

- `src/pdn_scanner/`
  основной код пайплайна
- `tests/`
  unit и integration tests
- `configs/`
  конфиги запуска, включая OCR/hybrid варианты
- `docs/`
  проектная документация
- `status/`
  release notes, implementation status, version
- `result.csv`
  финальный submission-файл
- `SUBMISSION.md`
  описание финального deliverable

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan share --out /tmp/pdn_run --config configs/default.yaml
```

Полезные конфиги:
- `configs/default.yaml`
  основной локальный запуск
- `configs/ocr.yaml`
  OCR-aware запуск
- `configs/hybrid_aggressive.yaml`
  более широкий OCR/hybrid профиль
- `configs/hybrid_conservative.yaml`
  более осторожный OCR/hybrid профиль

## Что лежит в финальном `result.csv`

Финальный список состоит из 15 записей и зафиксирован как release artifact.

Смысл этого списка:
- subject-level exports `customers.csv`, `logistics.csv`, `physical.parquet`
- внутренние employee / service / consent / handover / correspondence документы
- файлы, которые по задаче ближе к leak-like storage, чем к justified storage

## Что изменилось относительно старых версий

- проект переосмыслен из режима “найти любые ПДн” в режим поиска leak-like хранения
- добавлен genre-aware и storage-aware decision layer
- positive selection больше не равна “нашли поля = positive”
- `parquet`, `pdf`, `docx`, `rtf`, `xls`, `image/OCR` ветки присутствуют в коде и тестах
- финальный submission закреплён как стабильный release state, без audit/probe мусора

## Ключевые документы

- [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md)
- [docs/architecture.md](/Users/shttrkk/Downloads/ПДнDataset/docs/architecture.md)
- [docs/HACKATHON_CASE.md](/Users/shttrkk/Downloads/ПДнDataset/docs/HACKATHON_CASE.md)
