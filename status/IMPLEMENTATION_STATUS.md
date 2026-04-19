# Implementation Status

## Release State

Текущий репозиторий приведён к clean release состоянию перед защитой и публикацией.

- version: `0.1.1`
- final branch target: `main`
- final submission artifact: [result.csv](/Users/shttrkk/Downloads/ПДнDataset/result.csv)

## Кодовая готовность

| Область | Статус | Комментарий |
|---|---|---|
| CLI | done | `scan`, `validate-config`, `version` |
| Walker / format detection / dispatcher | done | production-ready для локального запуска |
| TXT / CSV / JSON / HTML | done | базовые устойчивые extractors |
| PDF / DOCX / RTF / XLS / Parquet | done | extractor branches реализованы |
| Image / OCR | done | включаются через OCR/hybrid configs |
| Legacy DOC | done | отдельная extraction ветка |
| Video | limited | best-effort unsupported fallback |
| Detectors | done | ordinary, government, payment, special, biometric |
| Validators | done | SNILS, INN, Luhn, bank, dates, MRZ hooks |
| Quality layer | done | anti-false-positive core layer |
| Leak context | done | genre-aware / storage-aware logic |
| UZ classifier | done | explainable final classifier |
| Cross-file logic | done | promotion/demotion across directory context |
| Privacy-safe reporting | done | CSV/JSON/Markdown without raw PII |

## Release decisions

- audit/probe/review artifacts удалены из tracked tree
- внутренние Codex handoff docs удалены
- конкурсный `result.csv` закреплён вручную
- документация переписана под leak-aware постановку

## Ограничения, которые честно стоит проговаривать

- OCR-heavy exploratory runs дороги по времени
- PDF/image ветка на этом корпусе не дала надёжного нового positive tail для финального submission
- финальный `result.csv` является release choice, а не автоматическим экспортом любого последнего exploratory rerun
