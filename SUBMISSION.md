# Submission Notes

## Что приложено

- `result.csv` — список файлов, содержащих признаки персональных данных, в формате:
  - `size,time,name`
- этот файл — краткое описание решения и способа запуска

## Как получен результат

Использован локальный CLI-пайплайн проекта `pdn-scanner` версии `0.1.0`:

`scan -> detect format -> dispatch extractor -> normalize -> detect -> validate -> classify -> report`

На текущем датасете в `v0.1.0` реально используются:

- extractors: `txt`, `csv`, `json`, `html`
- detectors: `email`, `phone`, `person_name`, `address`, `SNILS`, `INN`, `bank_card`
- privacy-safe reporting и отбор только положительных файлов для submission-артефакта

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan share --out /tmp/pdn_result_run --config configs/default.yaml
```

Далее `result.csv` собирается из положительных записей полного прогона с преобразованием в требуемый формат:

- `size` — размер файла в байтах
- `time` — `mtime` файла в формате `sep 26 18:31`
- `name` — имя файла без пути

## Что лежит в корне проекта

- `result.csv`
- `summary.csv`
- `report.json`
- `report.md`
