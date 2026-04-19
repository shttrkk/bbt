# Submission-Aligned Solution Plan

Этот план приведен к состоянию после подготовки актуального submission.

## Что уже принято как рабочее решение

- submission собирается локальным CLI-проходом
- `result.csv` содержит только positive-файлы в формате `size,time,name`
- основной вклад в качество дают не новые extractors, а quality-layer и строгий post-detection отбор

## Зафиксированный рабочий контур

`scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`

В текущем submission-контуре реально используются:

- `txt`
- `csv`
- `json`
- `html`

## Что обязательно учитывать дальше

### 1. Precision важнее nominal coverage

Расширение на `pdf/docx/xls/parquet/ocr` имеет смысл только если:

- extraction стабилен
- false positive не растет неконтролируемо
- новые форматы не ломают нынешний positive-only export

### 2. Quality-layer является частью core logic

Без следующих проверок submission становится заметно хуже:

- `is_template`
- `is_public_doc`
- `is_reference_data`
- suppression HTML / JS / token noise
- suppression structured `id/token` noise

### 3. Submission и roadmap нельзя больше смешивать

В документации должно быть явно разделено:

- текущее поставленное решение
- следующие итерации разработки

## Следующий этап после submission

1. Реализовать extraction для `pdf/docx/xls/parquet`.
2. Проверить recall/precision на шумных наборах до включения новых форматов в submission flow.
3. Только после этого рассматривать OCR и scanned-PDF fallback.
