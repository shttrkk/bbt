# Submission-Oriented PDN Analysis

Этот документ больше не описывает greenfield workspace. Актуальное состояние проекта определяется [SUBMISSION.md](/Users/shttrkk/Downloads/ПДнDataset/SUBMISSION.md).

## Главный вывод

Финальный submission был построен не на широкой поддержке всех форматов из кейса, а на precision-first контуре:

- рабочие extractors только для `txt`, `csv`, `json`, `html`
- quality-layer обязателен и находится в critical path
- positive-only export важнее широкого, но шумного покрытия

## Почему текущий submission выглядит именно так

- самые устойчивые сигналы были получены на текстовых и structured-lite форматах
- document-heavy и OCR-heavy форматы без качественного extraction дают слишком много шума
- public-policy, template и reference-like документы создают заметный false-positive риск без отдельного suppression слоя

## Что считается актуальным baseline

`scan -> detect format -> dispatch extractor -> normalize -> detect -> quality-layer -> classify -> report`

Реально значимые шаги:

- ordinary detection: `email`, `phone`, `person_name`, `address`, `birth_date_candidate`
- government detection: `SNILS`, `INN`
- payment detection: `bank_card`
- quality flags: `is_template`, `is_public_doc`, `is_reference_data`
- финальный фильтр: в submission уходят только файлы с `assigned_uz != NO_PDN`

## Ограничения текущей поставки

- `pdf/docx/xls/parquet/ocr` не используются как полноценные источники текущего submission-результата
- package version в коде пока не догнана до документированного submission-label `v0.1.1`
- sensitive/biometric path остается вспомогательным и не определяет основной результат текущего запуска

## Что важно сохранить при следующей итерации

1. Не размывать precision ради формального покрытия всех форматов.
2. Расширять extractors только вместе с anti-false-positive логикой.
3. Держать `SUBMISSION.md` главным источником истины для итоговой поставки.
