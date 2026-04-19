# PDN Scanner

CLI-проект для локального поиска персональных данных в смешанном файловом хранилище и подготовки privacy-safe submission-артефакта.

Актуальный источник истины по финальной поставке: [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md).

## Текущий статус

Документация приведена к состоянию финального submission-прохода.

- Submission-описание зафиксировано как `v0.1.1`.
- В коде package version пока остается `0.1.0`.
- Для итогового `result.csv` использовался локальный CLI-пайплайн:
  `scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`

## Что реально использовалось в submission

- Рабочие extractors: `txt`, `csv`, `json`, `html`
- Detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`, `birth_date_candidate`
- Quality-layer:
  - `is_template`
  - `is_public_doc`
  - `is_reference_data`
  - suppression HTML / JS / token noise
  - suppression structured `id/token` noise
- В `result.csv` попадают только positive-файлы, где `assigned_uz != NO_PDN`

## Что есть в кодовой базе, но не использовалось как полноценный источник submission

- Stub extractors: `pdf`, `docx`, `rtf`, `xls/xlsx`, `parquet`, `image`, `doc`, `mp4`
- OCR hooks есть в конфиге и extractor layer, но OCR не входил в финальный submission-контур
- Дополнительные валидаторы и hooks (`dates`, `bank`, `mrz`, `sensitive`) присутствуют частично, но не являются основой текущего submission-результата

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan ../share --out /tmp/pdn_submission_run --config configs/default.yaml
```

## Выходные артефакты

- `result.csv` — legacy submission-формат: `size,time,name`
- `SUBMISSION.md` — краткое описание результата и способа запуска
- Полный privacy-safe output run directory:
  - `summary.csv`
  - `report.json`
  - `report.md`

## Документация

- [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md)
- [docs/architecture.md](/Users/shttrkk/Downloads/ПДнDataset/docs/architecture.md)
- [docs/roadmap.md](/Users/shttrkk/Downloads/ПДнDataset/docs/roadmap.md)
- [status/IMPLEMENTATION_STATUS.md](/Users/shttrkk/Downloads/ПДнDataset/status/IMPLEMENTATION_STATUS.md)
