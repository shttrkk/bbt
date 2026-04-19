# Watch Candidates

Кандидаты вне текущего `result.csv`, которые стоит смотреть руками.

Источник:

- baseline: `/tmp/pdn_submission_run_v14/report.json`
- доп. разбор: `DOC/DOCX/RTF` по всему `share`, plus suspicious office/pdf tail
- в список попали файлы, где были `raw detections` до quality-layer suppression, либо есть явный extraction-gap

Короткий вывод:

- новых сильных suppressed-case с `person_name + companion` или `hard anchor + companion` не найдено;
- основная масса хвоста — шаблоны, публичные формы, орг-реквизиты и staff/public docs;
- самые правдоподобные manual-review кандидаты сейчас слабые и mostly form-like, но их можно отдельно руками проверить или пробно досабмитить.

## Review First

### `Прочее/%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD-%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BD%D0%B0-%D0%B2%D1%8B%D0%BF%D1%83%D1%81%D0%BA-%D0%BA%D0%B0%D1%80%D1%82%D1%8B.docx`

- probe status: `drop`
- metric: baseline `0.315` -> with this file `0.31142857142857`
- raw detections: `address=1`, `phone=1`
- suppressed by: `DOCX_PUBLIC_OR_TEMPLATE_PATH`
- verdict: выглядит сильнее остальных по surface-signal, но probe-сабмит уже показал ухудшение метрики, поэтому в следующие паки его лучше не брать
- sample: `ЗАЯВЛЕНИЕ ОБ ОТКРЫТИИ СЧЕТА, ВЫПУСКЕ, ПЕРЕВЫПУСКЕ БАНКОВСКОЙ КАРТЫ`

### `Прочее/Перечень документов.docx`

- probe status: `pending`
- raw detections: `phone=2`, `address=1`, `email=1`
- suppressed by: `DOCX_PUBLIC_OR_TEMPLATE_PATH`
- why worth a look: strongest contact-bundle outside baseline; возможно внутри есть не только checklist, но и заполненный пример
- sample: `Перечень документов конкурсного отбора ... Заявление на Конкурс. Анкета.`

### `Прочее/spd.docx`

- probe status: `pending`
- raw detections: `address=1`
- suppressed by: `DOCX_PATH_NOT_SHORTLISTED`
- why worth a look: consent for applicants; если файл не шаблонный и внутри есть заполненный блок субъекта, current path-shortlist может быть слишком узким
- sample: `СОГЛАСИЕ на обработку персональных данных для поступающих`

### `Прочее/%D0%B7%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5.docx`

- probe status: `pending`
- raw detections: `address=1`
- suppressed by: `DOCX_WEAK_SIGNALS_ONLY`
- why worth a look: типичный blank-like application; шанс небольшой, но это кандидат на ручную верификацию
- sample: `Проректору _______________________`

### `Прочее/Согласие участника конкурса.docx`

- probe status: `pending`
- raw detections: `address=1`
- suppressed by: `DOCX_WEAK_SIGNALS_ONLY`
- why worth a look: admission/grant consent doc; если в файле есть реальные заполненные данные, current weak-signal suppression может быть слишком жёстким
- sample: `Согласие на обработку персональных данных участника конкурсного отбора`

### `Прочее/Согласие законного представителя.docx`

- probe status: `pending`
- raw detections: `address=1`
- suppressed by: `DOCX_WEAK_SIGNALS_ONLY`
- why worth a look: аналогичный случай, но для законного представителя
- sample: `Согласие на обработку персональных данных законного представителя`

## Wide But Noisy

Эти файлы я бы не сабмитил без ручной проверки, но вынес для полноты.

### `Прочее/Договор.docx`

- raw detections: `inn_legal_entity=1`, `bank_account=1`
- suppressed by: `DOCX_WEAK_SIGNALS_ONLY`
- comment: пока выглядит как орг-реквизиты договора на грант, не физлицо

### `Прочее/Согласие_ПДн_(map.ncpti.ru).rtf`

- raw detections: `address=1`, `inn_legal_entity=1`
- suppressed by: `OFFICE_WEAK_SIGNALS_ONLY`
- comment: это уже проверенный FP после подключения `RTF`; внутри публичный consent сайта с реквизитами оператора

## Not Worth Review

Ниже не кандидаты, а masquerade/junk:

- `Прочее/Application-Offer-Form.rtf`
- `Прочее/Azov_conf-application.rtf`
- `Прочее/Prikaz-1846_Application2-Act.rtf`
- `Прочее/Rasporiagenie-1129-p_Application-sample.rtf`

У всех размер около `537` байт, и содержимое — HTML `500 Internal Server Error`, а не RTF.
