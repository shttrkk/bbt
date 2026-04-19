# Codex Handoff

Если новый Codex попадает в этот репозиторий без контекста, начинать надо отсюда.

Что прочитать сначала:
- `docs/codex/STATE.md`
- `docs/codex/PLAYBOOK.md`
- `docs/codex/PDF_PROMPT_HANDOFF.md` если продолжается работа по PDF
- `SUBMISSION.md`

Быстрый статус:
- стабильный checkpoint commit: `f6c3603` (`checkpoint before anchor-bundle expansion`)
- в рабочем дереве поверх checkpoint есть незакоммиченные изменения:
  - `src/pdn_scanner/config.py`
  - `src/pdn_scanner/extractors/image.py`
  - `src/pdn_scanner/extractors/ocr.py`
  - `src/pdn_scanner/extractors/office_legacy.py`
  - `src/pdn_scanner/extractors/pdf.py`
  - `src/pdn_scanner/extractors/rtf.py`
  - `src/pdn_scanner/extractors/textutil.py`
  - `src/pdn_scanner/quality/anti_fp.py`
  - `src/pdn_scanner/submission/cross_file.py`
  - `tests/unit/test_cross_file_promotion.py`
  - `tests/unit/test_image_extractor.py`
  - `tests/unit/test_legacy_extractors.py`
  - `tests/unit/test_ocr_shortlist.py`
  - `tests/unit/test_pdf_extractor.py`
  - `tests/unit/test_quality_layer.py`
  - `configs/default.yaml`
  - `configs/fast.yaml`
  - `configs/ocr.yaml`
  - `configs/hybrid_conservative.yaml`
  - `configs/hybrid_aggressive.yaml`
  - `configs/shortlists/hybrid_conservative.txt`
  - `configs/shortlists/hybrid_aggressive.txt`
  - `tools/build_shortlist_corpus.py`
  - `tools/build_probe_submissions.py`
  - `tools/make_hybrid_submission.py`
  - `watch_candidates.md`
  - `candidate_submission_review.csv`
  - `candidate_submission_review_wide.csv`
  - `submission_probes/*`
- есть пользовательские изменения, которые не надо трогать без запроса:
  - удалены `HACKATHON_CASE.md`, `HACKATHON_PDN_ANALYSIS.md`, `HACKATHON_SOLUTION_PLAN.md`
  - изменён `SUBMISSION.md`

Текущее рабочее состояние:
- актуальный `result.csv` в корне уже пересобран из `/tmp/pdn_submission_run_v14`
- актуальный `watch.md` в корне отражает тот же состав positive-файлов (`14`)
- последний полный подтверждённый прогон: `/tmp/pdn_submission_run_v14`
- в `result.csv` сейчас `14` data rows
- текущий полный тестовый набор: `81 passed`
- PDF-ветка доведена до подтверждённого состояния:
  - page-wise extractor + fallback + page scoring реализованы
  - cheap signature precheck добавлен
  - confirmed outcome на датасете: `pdf_positive = 0`
- OCR и shortlist-ветка реализованы, но confirmed прироста не дали:
  - `share/Архив сканы` aggressive shortlist: `150 files`, `0 detections`, `0 delta`
  - `share/Выгрузки/Сайты/Доки` aggressive shortlist: `32 files`, `0 detections`, `0 delta`
  - `share/Прочее` conservative shortlist: `1791 files`, `0 detections`, `0 delta`
  - shortlist corpora `conservative/aggressive`: по `181` файлов, итог `0` новых строк против `v14`
- `RTF/DOC` extraction через `textutil` добавлен:
  - это нашло один новый office FP (`Согласие_ПДн_(map.ncpti.ru).rtf`), который уже подавлен
- candidate/review артефакты подготовлены:
  - `watch_candidates.md`
  - `candidate_submission_review.csv`
  - `candidate_submission_review_wide.csv`
  - `submission_probes/*.csv`
- English / mixed-form ordinary detection усилен:
  - `src/pdn_scanner/detectors/ordinary.py`
  - `tests/unit/test_detectors.py`
  - добавлены Latin `person_name`, English `address` / `birth_place`, international `phone` по keyword-context
  - добавлен extraction для multiline/composite labels вроде `Mailing Address`, `Place of Birth`, `Адрес выезда инженера`
  - anti-noise для company names сохранён
- ручной пользовательский результат:
  - baseline `result.csv` дал метрику `0.315`
  - baseline + `candidate_submission_review.csv` дал `0.29714285714286`
  - baseline + `probe_01_card_issue_form.csv` дал `0.31142857142857`
  - значит review-пачка содержит FP и должна проверяться probe-сабмитами по одному файлу
  - `card_issue_form` уже считать `drop`, не возвращать его в комбинированные probe-паки

Если нужно быстро продолжить работу:
1. Проверить `git status`.
2. Прочитать `docs/codex/STATE.md`.
3. Прочитать `docs/codex/PLAYBOOK.md`.
4. Если нужно понять, как именно была закрыта PDF-ветка, прочитать `docs/codex/PDF_PROMPT_HANDOFF.md`, затем сверить с `docs/codex/STATE.md`.
5. Если нужна ручная проверка новых кандидатов, открыть `watch_candidates.md` и `submission_probes/README.txt`.
6. Если нужен безопасный rollback, использовать commit `f6c3603`.
7. Если продолжается исследование качества, смотреть сначала `watch_candidates.md`, потом `summary.csv`/`report.json` последнего релевантного частичного или полного прогона.
