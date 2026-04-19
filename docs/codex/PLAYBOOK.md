# Playbook

## Полезные команды

Полный прогон:

```bash
PYTHONPATH=src .venv/bin/python -m pdn_scanner.cli scan share --out /tmp/pdn_submission_run_vN --config configs/default.yaml
```

Собрать корневой `result.csv` из `summary.csv`:

```bash
python3 - <<'PY'
import csv
from datetime import datetime
from pathlib import Path
root = Path('/Users/shttrkk/Downloads/ПДнDataset')
summary_path = Path('/tmp/pdn_submission_run_vN/summary.csv')
output_path = root / 'result.csv'
rows = []
with summary_path.open(encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        if row['assigned_uz'] == 'NO_PDN':
            continue
        rel_path = row['rel_path']
        file_path = root / 'share' / rel_path
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%b %d %H:%M').lower()
        rows.append((Path(rel_path).name.lower(), stat.st_size, mtime, Path(rel_path).name))
rows.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
with output_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['size', 'time', 'name'])
    for _, size, mtime, name in rows:
        writer.writerow([size, mtime, name])
print(f'wrote {output_path} rows={len(rows)}')
PY
```

Полный тестовый набор:

```bash
PYTHONPATH=src .venv/bin/pytest
```

## Как анализировать очередной эксперимент
1. Сначала смотреть `summary.csv`.
2. Потом смотреть только positive-файлы и их `classification_reasons`.
3. Если появился новый формат в positives, обязательно руками проверить evidence через `watch.md` или прямой re-run на одном файле.
4. Никогда не тащить новый формат в submission только потому, что extractor заработал.

## Приоритет следующих шагов

### Наиболее перспективно
- probe-сабмиты по одному кандидату из `submission_probes/`
- content-driven candidate mining для `doc/docx/rtf`, а не path-driven shortlist
- ручная проверка `watch_candidates.md`

### Менее перспективно
- broad `pdf`
- broad `image OCR`
- дальше ослаблять `html`
- дальше ослаблять `xls`
- broad `docx`

## Текущие полезные артефакты
- baseline full run: `/tmp/pdn_submission_run_v14`
- review watchlist: `watch_candidates.md`
- narrow review tail: `candidate_submission_review.csv`
- wide review tail: `candidate_submission_review_wide.csv`
- ready-to-submit probes: `submission_probes/*.csv`
- English/mixed-form detector update:
  - `src/pdn_scanner/detectors/ordinary.py`
  - `tests/unit/test_detectors.py`
  - current test status: `81 passed`

## Как работать с probe submission
1. Не менять основной `result.csv`, пока probe не доказал прирост.
2. Запускать сначала single-file probes:
   - `probe_02_document_checklist.csv`
   - `probe_03_applicant_consent_spd.csv`
   - `probe_05_contest_consent.csv`
   - `probe_06_guardian_consent.csv`
   - `probe_01_card_issue_form.csv` не использовать для новых паков: already `drop` по метрике `0.31142857142857`
3. Только потом запускать пакеты:
   - `probe_07_checklist_plus_spd.csv`
   - `probe_08_consents_only.csv`
   - `probe_09_review_no_card.csv`
4. `probe_10_wide_noise_check.csv` использовать только как sanity-check на шум.

## Отдельный приоритет сейчас
- не делать broad English loosening в public/html хвосте
- использовать English improvements как усиление content-driven candidate mining
- если нужен targeted run, собирать shortlist по personal labels:
  - `requester`
  - `full name`
  - `mailing address`
  - `place of birth`
  - `phone: +`

## Что проверять перед новой сдачей
- `result.csv` содержит только positive-записи
- нет пустых полей
- заголовок строго `size,time,name`
- имя файла строго `result.csv`
- если появился новый positive, он должен проходить ручную проверку по смыслу, а не только по regex
- если probe ухудшил метрику, не переносить его в основной `result.csv`

## Как откатиться

Вернуться к стабильной точке:

```bash
git checkout f6c3603 -- src tests docs result.csv watch.md configs status
```

Не трогать без отдельного решения:
- `SUBMISSION.md`
- пользовательские удаления корневых `HACKATHON_*.md`
