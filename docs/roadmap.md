# Roadmap

## Текущее состояние

Версия `0.1.1` считается release-ready для защиты:
- leak-aware logic внедрена
- финальный `result.csv` закреплён
- документация синхронизирована с кодом
- тесты проходят

## Что уже закрыто

- переход от `PD presence` к `leak-aware` интерпретации
- genre-aware и storage-aware decision logic
- `parquet` extraction для subject-level exports
- `pdf` extraction с fallback и selective OCR hooks
- `docx`, `rtf`, `xls`, `image`, `doc` extraction branches
- explainable storage classification и UZ logic
- cross-file promotion/demotion logic

## Что считается будущими итерациями, а не частью релизной фиксации

- performance tuning OCR-heavy runs
- дополнительное сужение public/report false positives
- более агрессивная office/image recall без потери precision
- автоматический release builder для фиксированного submission state

## Принцип дальнейшего развития

Любое расширение coverage должно подтверждать не “нашли больше полей”, а:
- лучше отделяет target leak от justified storage
- не ломает precision на public/official/template хвосте
- не приводит к захламлению финального `result.csv`
