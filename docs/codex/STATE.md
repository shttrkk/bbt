# Current State

## Цель
Собрать `result.csv` для хакатонного задания: список только тех файлов, которые содержат защищаемые персональные данные.

Формат файла:
- `size,time,name`

Текущая рабочая гипотеза:
- не ловить любое `ФИО`
- искать персонализирующие связки
- публичные и шаблонные документы не тащить в submission
- не считать baseline священным: probe-сабмиты можно и нужно тестировать отдельно
- при этом не добавлять файл в основной `result.csv` без evidence и метрики

## Что уже реализовано

### Детекция
- добавлена иерархия `entity_category -> entity_subtype`
- каждая находка хранит позицию, фрагмент и confidence
- покрыты:
  - ordinary
  - government
  - payment
  - biometric
  - special categories
- ordinary detector дополнительно усилен под English/mixed forms:
  - Latin `person_name` для label-driven personal docs
  - English `address`
  - English `birth_place`
  - international `phone` по keyword-context
  - multiline/composite labels (`Mailing Address`, `Place of Birth`, `Адрес выезда инженера`)
  - anti-noise на company names сохранён

### Quality layer
- жёсткое подавление шумного `html`
- `xls` extractor и `xls` gate
- `docx` extractor и `docx` shortlist/gate
- `rtf/doc` extraction через системный `textutil`
- `rtf/doc` office gate
- PDF public/legal/report/contact suppression
- image OCR noise suppression
- cross-file promotion для пары `customers.csv + logistics.csv`
- cross-file promotion по shared linkage hashes и small-directory bundle

### Submission logic
- `person_name` alone и `address` alone не считаются сильным сигналом сами по себе
- `customers.csv` и `logistics.csv` возвращаются в positive только как `CROSS_FILE_PERSON_ADDRESS_BUNDLE`
- расширена логика personal anchors:
  - `person_name`
  - `inn_individual`
  - `snils`
  - `passport_*`
  - `driver_license`
  - `mrz`
  - `bank_card`
- companions:
  - `address`
  - `phone`
  - `email`
  - `birth_date`
  - `birth_place`
- weak singletons демотятся:
  - `person_name`
  - `address`
  - `phone`
  - `email`
  - `birth_date`
  - `birth_place`
- защита от org-noise сохранена:
  - `inn_legal_entity` не должен сам поднимать positive
  - `bank_account + bik` без person-context не считать персональным bundle
  - `sostav_gr.xls` должен подавляться как public staff/contact sheet

## Последний подтверждённый результат
- последний прогон: `/tmp/pdn_submission_run_v14`
- positives: `14`
- форматы в positives:
  - `csv`: 4
  - `txt`: 10
- `pdf/xls/docx/html` в итоговом `result.csv` сейчас нет
- baseline метрика по пользователю: `0.315`
- `probe_01_card_issue_form.csv`: `0.31142857142857` -> confirmed negative candidate (`drop`)

Текущий состав positives:
- `Выгрузки/Логистика/customers.csv`
- `Выгрузки/Логистика/logistics.csv`
- `Выгрузки/дочерние предприятия/Billing/full/customers.csv`
- `Выгрузки/дочерние предприятия/Billing/full/logistics.csv`
- 10 файлов из `Выгрузки/дочерние предприятия/Employes/*.txt`

## Что уже показало себя хорошо
- вырезание почти всего `html` подняло score с `0.24` до `0.31`
- широкий `xls` recall уронил score до `0.24857`
- возврат к жёсткому `xls` gate вернул baseline
- улучшение `person_name` extraction в `txt` повысило качество evidence, но не изменило итоговый список файлов
- English/mixed-form improvement в `ordinary.py` улучшил recall для label-driven personal docs и исправил extraction узких адресов в service/home-office формах
- `pdf` precheck и page-wise extractor убрали runtime-noise без прироста FP
- `rtf/doc` extraction через `textutil` расширил покрытие office-хвоста
- probe-сабмиты поверх baseline подготовлены в `submission_probes/`

## Что уже пробовали и не дало прироста
- broad `xls`
- broad `docx`
- расширение bundle-логики на personal anchors
- PDF-ветка теперь реализована и подтверждена итоговым прогоном, но на этом датасете не дала новых валидных positives
- OCR shortlist-mode по `Архив сканы`
- OCR shortlist-mode по `Выгрузки/Сайты/Доки`
- OCR shortlist-mode по `Прочее`
- shortlist corpora `conservative/aggressive`
- aggressive hybrid configs
- `candidate_submission_review.csv` в сумме ухудшил метрику до `0.29714285714286`
- `probe_01_card_issue_form.csv` ухудшил метрику до `0.31142857142857`

На текущем датасете это не дало новых валидных submission-файлов.

## English / mixed-form update
- файлы:
  - `src/pdn_scanner/detectors/ordinary.py`
  - `tests/unit/test_detectors.py`
- текущий тестовый статус после этого: `81 passed`
- что закрыто:
  - `Requester: John Michael Carter`
  - `Mailing Address: 221B Baker Street, Apt 5, London NW1 6XE`
  - `Place of Birth: New York, USA`
  - international phones вроде `+1 (202) 555-0147`
  - multiline address blocks после label
- что важно:
  - English coverage усилили точечно для personal forms, а не broadly по narrative/public web
  - быстрый grep по корпусу показал, что вне public HTML реальный English tail маленький
  - это recall foundation под targeted candidate runs, а не подтверждённый submission delta само по себе

## Известные важные правила из лекции
- `ФИО` само по себе: слабый сигнал
- `адрес` сам по себе: слабый сигнал
- `ФИО + адрес` или `ФИО + контакт`: сильная связка
- также сильны:
  - паспорт
  - СНИЛС
  - ИНН физлица
  - платёжные данные
  - биометрия
  - специальные категории
- публично опубликованные данные не надо автоматически считать защищаемыми ПД

## PDF-итог
- extractor теперь page-wise:
  - primary: `pypdf`
  - fallback: `pdfplumber`
  - page score: `length/printable_ratio/alpha_ratio/word_count/avg_token_length`
  - page states: `good/suspicious/empty/error`
- есть cheap signature precheck:
  - `1465` real PDF
  - `188` HTML masquerade
  - `2` JSON masquerade
  - `3` other non-PDF masquerade
- PDF gate ужесточён:
  - public/legal/report/protocol/contact PDFs подавляются раньше strong bundle
  - narrative/special mentions без person linkage не поднимаются
  - false positives по `driver_license` из подстроки `ВУЗ` и по `passport` из дальнего контекста закрыты
- итог confirmed run `v14`:
  - `pdf_with_detections = 0`
  - `pdf_positive = 0`

## OCR / Hybrid итог
- OCR реализован через `tesseract` `rus+eng`
- image OCR и selective PDF OCR работают только в shortlist-mode
- shortlist policy теперь manifest/config-driven:
  - `configs/hybrid_conservative.yaml`
  - `configs/hybrid_aggressive.yaml`
  - `configs/shortlists/*`
- helper tools:
  - `tools/build_shortlist_corpus.py`
  - `tools/make_hybrid_submission.py`
  - `tools/build_probe_submissions.py`
- фактический outcome:
  - shortlist `conservative`: `181 files`, `9 positives`, `0 delta` против `v14`
  - shortlist `aggressive`: `181 files`, `9 positives`, `0 delta` против `v14`
  - `Прочее` partial run: `1791 files`, `0 detections`
  - `Архив сканы` partial run: `150 files`, `0 detections`
  - `Выгрузки/Сайты/Доки` partial run: `32 files`, `0 detections`

## Candidate / Review артефакты
- `watch_candidates.md` содержит review-first кандидатов вне baseline
- `candidate_submission_review.csv` содержит узкий review-tail
- `candidate_submission_review_wide.csv` содержит более шумный tail
- `submission_probes/` содержит full ready-to-submit probe-файлы по одному кандидату и малыми пачками

Самые правдоподобные review-кандидаты сейчас:
- `Прочее/%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD-%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BD%D0%B0-%D0%B2%D1%8B%D0%BF%D1%83%D1%81%D0%BA-%D0%BA%D0%B0%D1%80%D1%82%D1%8B.docx`
- `Прочее/Перечень документов.docx`
- `Прочее/spd.docx`
- `Прочее/%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5.docx`
- `Прочее/Согласие участника конкурса.docx`
- `Прочее/Согласие законного представителя.docx`

Проверенный FP после подключения `RTF`:
- `Прочее/Согласие_ПДн_(map.ncpti.ru).rtf`
- raw detections: `address + inn_legal_entity`
- теперь подавляется как `OFFICE_WEAK_SIGNALS_ONLY`

Проверенный probe-negative:
- `probe_01_card_issue_form.csv`
- пользовательская метрика: `0.31142857142857`
- verdict: `drop`

## Рискованные места
- не возвращать шумные `html`
- не возвращать `sostav_gr.xls`
- осторожно с `docx`-договорами и реквизитами организаций
- не считать `inn_legal_entity + address/phone/email` персональными данными
- PDF extraction остаётся шумной по runtime warnings на реально повреждённых PDF, но это не влияет на итоговый submission
- `candidate_submission_review.csv` уже показал, что слабые office candidates легко портят метрику
- в полном `v14` нет файлов с `detections != 0` и итогом `NO_PDN`, поэтому один только cross-file linkage без новых detections прироста почти не даст
