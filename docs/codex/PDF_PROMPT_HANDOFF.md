# PDF Prompt Handoff

Этот файл теперь нужен в основном как исторический лог по PDF-ветке.
Для актуального состояния приоритетнее:
- `docs/codex/START_HERE.md`
- `docs/codex/STATE.md`
- `docs/codex/PLAYBOOK.md`

Этот файл фиксирует именно то, что было сделано по PDF-задаче в последнем прерванном промпте, и что осталось недоделанным.

## Update: resolved state

После этого handoff PDF-ветка была доведена до подтверждённого результата:
- cheap signature precheck добавлен
- false positives по `driver_license`/`passport` в PDF закрыты
- подтверждённый прогон: `/tmp/pdn_submission_run_v14`
- итог по датасету:
  - `pdf_with_detections = 0`
  - `pdf_positive = 0`
  - `result.csv` не изменился по составу positives (`14` rows)
- после этого дополнительно проверены shortlist/hybrid ветки:
  - `share/Прочее` conservative shortlist: `1791 files`, `0 detections`
  - `share/Выгрузки/Сайты/Доки` aggressive shortlist: `32 files`, `0 detections`
  - shortlist corpora `conservative/aggressive`: по `181` files, `0 delta` против `v14`

Итоговый practical verdict:
- PDF extractor оставляем в коде
- PDF не является текущим источником submission growth на этом датасете
- новые усилия сейчас выгоднее тратить на office/content-driven candidates, а не на broad PDF work

Для актуального состояния приоритетнее читать:
- `docs/codex/STATE.md`
- `docs/codex/START_HERE.md`

Update after later iterations:
- после PDF/OCR/office итераций дополнительно усилен `ordinary` detector для English/mixed personal forms
- файлы:
  - `src/pdn_scanner/detectors/ordinary.py`
  - `tests/unit/test_detectors.py`
- текущий общий тестовый статус: `81 passed`
- practical verdict по PDF не меняется:
  - PDF остаётся не источником confirmed delta
  - более перспективны targeted office/probe/content-driven candidate runs

## Контекст
Пользователь попросил реализовать PDF-логику такого типа:
- page-wise parsing, а не whole-file blob
- native extraction на каждую страницу
- fallback backend для пустых/подозрительных страниц
- выбор лучшего page text по quality score
- quality signals на страницу
- page statuses: `good / suspicious / empty / error`
- file-level metadata summary
- PDF не должен становиться positive просто потому, что из него удалось вытащить текст
- positive только по strong personal signal:
  - hard personal anchor
  - либо personal anchor + companion
- public/legal/article/report/brochure/org-contact pdf должны подавляться
- OCR пока только как hook/flag, без массового OCR

## Что точно успели сделать в коде

### 1. Новый PDF extractor реализован
Файл:
- `src/pdn_scanner/extractors/pdf.py`

Что там теперь есть:
- page-wise extraction вместо `UnsupportedExtractor`
- основной backend: `pypdf`
- fallback backend: `pdfplumber`
- fallback вызывается на странице, если primary page status равен:
  - `empty`
  - `suspicious`
  - `error`
- лучший результат выбирается не по правилу “первый непустой”, а функцией `_select_best_page_result`

### 2. Page quality scoring реализован
В `pdf.py` есть:
- `PageExtractionResult`
- `_compute_text_metrics`
- `_classify_page`

Считаются сигналы:
- `length`
- `printable_ratio`
- `alpha_ratio`
- `word_count`
- `avg_token_length`
- агрегированный `score`

Статусы страниц:
- `good`
- `suspicious`
- `empty`
- `error`

### 3. File-level PDF metadata реализован
В `ExtractedContent.metadata` extractor пишет:
- `pdf_summary`
  - `page_count`
  - `status_counts`
  - `fallback_used_pages`
  - `ocr_candidate_pages`
  - `has_selective_ocr_candidates`
- `page_extraction`
  - по каждой странице:
    - `page_number`
    - `selected_backend`
    - `selected_status`
    - `selected_score`
    - `length`
    - `printable_ratio`
    - `alpha_ratio`
    - `word_count`
    - `avg_token_length`
    - список backend attempts

Также extractor пишет warning вида:
- `Selective OCR may help on pages: ...`

То есть hooks под selective OCR уже заложены, но OCR не реализован.

### 4. PDF file-level suppression / selection добавлен
Файл:
- `src/pdn_scanner/quality/anti_fp.py`

Что добавлено:
- `_apply_pdf_selection`
- `_has_strong_pdf_bundle`
- `_looks_like_org_contact_pdf`
- `_has_only_weak_pdf_signals`
- `_has_narrative_only_pdf_signals`

PDF selection logic сейчас такая:
- positive только если есть `PDF_STRONG_BUNDLE`
- public source PDFs подавляются
- public/legal/report-like PDFs подавляются
- org-contact PDFs подавляются
- email-only / phone-only / address-only / org requisites-only PDFs подавляются
- narrative/special-like weak PDFs без person linkage подавляются

### 5. PDF-тесты добавлены
Файлы:
- `tests/unit/test_pdf_extractor.py`
- `tests/unit/test_quality_layer.py`

Что покрыто тестами:
- page quality metrics
- page-wise metadata extraction
- suppression public policy pdf
- positive для `inn_individual + phone` в PDF
- suppression org requisites-only PDF

### 6. Тестовый набор проходил
Последний полностью подтверждённый локальный запуск тестов перед прерыванием:
- `54 passed`

Это значит:
- extractor код компилируется
- unit/integration test suite на момент последнего прогона была зелёной

## Что начали делать, но не успели довести до конца

### 1. Полный прогон по датасету с новым PDF extractor
Был запущен:
- `/tmp/pdn_submission_run_v11`

Но пользователь прервал ход во время ожидания завершения.

Важно:
- итог `v11` не был зафиксирован как подтверждённый результат
- `result.csv` по `v11` не пересобирался
- `watch.md` по `v11` не обновлялся
- `keep/maybe/drop` анализ по PDF не был построен

То есть `v11` сейчас нельзя считать завершённым и trustworthy без перепроверки.

### 2. Не добавлен cheap precheck по сигнатуре PDF
Во время прогона стало видно, что в корпусе много файлов с расширением `.pdf`, которые на самом деле:
- HTML
- JSON
- error pages
- другой мусор

По логам были предупреждения типа:
- `invalid pdf header: b'<html'`
- `invalid pdf header: b'<!DOC'`
- `invalid pdf header: b'{"_re'`
- `EOF marker not found`

Вывод:
- нужен cheap signature/header precheck в `pdf.py`
- если файл не начинается как настоящий PDF, не надо вообще открывать его через `pypdf` и `pdfplumber`
- сейчас это ещё не сделано

Это, вероятно, следующая обязательная оптимизация.

### 3. Не собран список `keep / maybe / drop` по PDF
План был такой:
- `keep`: PDF, которые реально стали positive
- `maybe`: PDF с detections, но без final promotion
- `drop`: public/legal/article/report/org-contact noise

Этот анализ не был выполнен из-за прерванного прогона.

### 4. Не обновлены handoff/docs под итоговый PDF run
`docs/codex/STATE.md` пока отражает состояние до PDF-ветки.
Этот файл (`PDF_PROMPT_HANDOFF.md`) нужен именно чтобы закрыть этот разрыв.

## Что видно уже сейчас по качеству решения

### Хорошее
- архитектурно PDF extractor теперь сделан правильно
- page-wise metadata уже есть
- fallback chain уже есть
- selective OCR hook уже есть
- file-level suppression заложен правильно: PDF не должен стать positive просто потому, что из него вытащили текст

### Слабые места
- нет signature precheck
- из-за этого реальные прогоны шумные по warnings и, вероятно, медленнее нужного
- не подтверждено, даёт ли PDF хоть один полезный новый positive на этом датасете
- не подтверждено, не вернёт ли PDF лишний public noise

## Какой был следующий план на момент прерывания
Следующие шаги должны были быть такими:

1. Дождаться или перезапустить полный прогон по PDF.
2. Сразу после прогона:
   - посмотреть `summary.csv`
   - вытащить только `format == pdf`
   - разбить на `keep / maybe / drop`
3. Добавить cheap precheck по сигнатуре файла:
   - настоящие PDF пропускать
   - `<html`, `<!DOC`, `{...}`, и подобное уводить в `EMPTY` или `PARTIAL` без открытия backend-ами PDF
4. Только после этого принимать решение:
   - оставлять PDF в основном пайплайне
   - или временно держать extractor, но не использовать для submission

## Что обязательно сказать следующему Codex
- не считать PDF-ветку завершённой
- не использовать `v11` как подтверждённый результат без перепроверки
- первым делом добавить cheap signature precheck
- потом заново прогнать scan
- потом построить `keep / maybe / drop` именно по PDF
- только потом обновлять `result.csv`

## Файлы, изменённые в этом промпте
- `src/pdn_scanner/extractors/pdf.py`
- `src/pdn_scanner/quality/anti_fp.py`
- `tests/unit/test_quality_layer.py`
- `tests/unit/test_pdf_extractor.py`
- `docs/codex/START_HERE.md`
- `docs/codex/PDF_PROMPT_HANDOFF.md`

## Стабильная точка rollback
Если PDF-эксперимент надо полностью отбросить:
- stable checkpoint commit: `f6c3603`
- это `checkpoint before anchor-bundle expansion`

Важно:
- поверх него уже есть другие незакоммиченные изменения не только по PDF
- поэтому откатывать нужно осознанно, а не через `reset --hard`
