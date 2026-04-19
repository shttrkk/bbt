# Submission Notes

## Что приложено

- `result.csv` — список файлов, содержащих признаки персональных данных, в формате:
  - `size,time,name`
- этот файл — краткое описание решения и способа запуска

## Как получен результат

Использован локальный CLI-пайплайн проекта `pdn-scanner` версии `0.1.1`:

`scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`

На текущем подтверждённом прогоне `v14` (`/tmp/pdn_submission_run_v14`) в итоговый submission реально попали:

- extractors: `txt`, `csv`, `json`, `html`
- detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`, `birth_date_candidate`
- quality-layer:
  - `is_template`
  - `is_public_doc`
  - `is_reference_data`
  - suppression HTML / JS / token noise
  - suppression structured `id/token` noise
- privacy-safe reporting и отбор только положительных файлов для submission-артефакта

Важно:

- `pdf` extractor теперь реализован page-wise (`pypdf` + `pdfplumber` fallback, page scoring, selective OCR hooks, signature precheck), но на подтверждённом прогоне не дал ни одного валидного positive-файла;
- `docx/xls/parquet/ocr` не добавили новых positive-файлов в подтверждённый submission;
- в submission включены только positive-файлы, найденные текущим runnable CLI;
- сам submission `result.csv` сохраняется в legacy-формате конкурса: `size,time,name`.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan ../share --out /tmp/pdn_submission_run --config configs/default.yaml
```

Далее `result.csv` собирается из положительных записей полного прогона с преобразованием в требуемый формат submission:

- `size` — размер файла в байтах
- `time` — `mtime` файла в формате `sep 26 18:31`
- `name` — имя файла без пути

Правило отбора:

- в `result.csv` попадают файлы, для которых итоговый `assigned_uz != NO_PDN`
- это означает, что шаблоны, public-policy-like документы и reference-like structured файлы без устойчивых PD signals в submission не попадают

## Что лежит в корне проекта

- `result.csv`
- `SUBMISSION.md`

Полные privacy-safe артефакты полного прогона лежат в output-директории запуска:

- `summary.csv`
- `report.json`
- `report.md`
