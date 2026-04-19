# Submission Notes

## Финальный deliverable

В корне репозитория зафиксирован финальный конкурсный файл:

- [result.csv](/Users/shttrkk/Downloads/ПДнDataset/result.csv)

Формат:

```text
size,time,name
```

Этот файл является финальным release artifact и в текущей версии репозитория не должен пересобираться автоматически.

## Зафиксированный итоговый `result.csv`

```csv
size,time,name
1750,mar 23 09:57,akt_priema_peredachi_rabochego_mesta.txt
1385,mar 23 09:57,anketa_dms.txt
650666,nov 09 19:41,customers.csv
650666,sep 26 21:59,customers.csv
1562,mar 23 09:57,doverennost_na_poluchenie_posylki.txt
3563943,nov 09 19:41,logistics.csv
3563943,sep 26 21:59,logistics.csv
1689,mar 23 09:57,perepiska_email_dostavka_kresla.txt
1542,mar 23 09:57,raspiska_poluchenie_noutbuka.txt
1391,mar 23 09:57,servisnaya_zayavka_vyezd_inzhenera.txt
2138,mar 23 09:57,soglasie_na_obrabotku_pd.txt
1386,mar 23 09:57,zayavka_kompensaciya_interneta.txt
1257,mar 23 09:57,zayavka_na_propusk_v_zhk.txt
1372,mar 23 09:57,zayavlenie_dostavka_oborudovaniya_domoi.txt
8879363,sep 26 22:01,physical.parquet
```

## Логика финальной поставки

Задача решается в leak-aware постановке:

- не любые ПДн считаются проблемой
- target = подозрительное, избыточное или необоснованное хранение ПДн
- justified/public/storage-safe документы должны подавляться

Это означает, что в финальный список попадают не “все файлы с ПДн”, а только те, которые похожи на:
- внутренние персональные формы
- employee/home-office/service docs
- consent/authority/request/handover docs
- переписку с персональными bundle-сигналами
- subject-level выгрузки физлиц

## Базовый pipeline

Проект использует локальный CLI-проход:

`scan -> detect format -> dispatch extractor -> detect -> quality-layer -> leak-context -> classify -> report`

Ключевые компоненты:

- extractors:
  `txt`, `csv`, `json`, `parquet`, `pdf`, `docx`, `rtf`, `xls/xlsx`, `html`, `image`, `doc`
- detectors:
  ordinary, government, payment, sensitive, biometric
- quality-layer:
  template/public/reference suppression
  structured-noise suppression
  format-specific suppression для `html/pdf/docx/xls/image`
- leak-aware layer:
  genre detection
  risk / justification / noise scoring
  storage class
- UZ classifier:
  `UZ-1..UZ-4` или `NO_PDN`

## Что важно для защиты

Финальный `result.csv` фиксирован как release decision.

Это значит:
- он не обязан совпадать с любым текущим exploratory rerun
- он отражает финально выбранный submission set
- код и документация объясняют, почему именно такие файлы считаются целевыми leak-like объектами

## Как запускать проект

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan share --out /tmp/pdn_run --config configs/default.yaml
```

Выходы обычного запуска:
- `summary.csv`
- `report.json`
- `report.md`

Они используются как privacy-safe технические артефакты анализа, но не заменяют финальный зафиксированный `result.csv`.
