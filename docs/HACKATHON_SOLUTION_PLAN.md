# Final Solution Plan

## Итоговая формула решения

1. Обойти файловое хранилище.
2. Извлечь текст/структуру из разных форматов.
3. Найти кандидатные персональные сигналы.
4. Убрать шаблоны, public docs, reference noise и format-specific шум.
5. Определить жанр документа и контекст хранения.
6. Оценить, похож ли файл на leak-like storage.
7. Классифицировать итоговый риск и подготовить privacy-safe отчёт.
8. Зафиксировать финальный submission отдельным `result.csv`.

## Почему решение именно такое

- entity detection сама по себе недостаточна
- основные ошибки возникают на public/template/report хвосте
- качество обеспечивается не только detector-ами, но и quality + leak-context слоями

## Что важно на защите

- показать, что решение explainable
- показать, что есть разделение `TARGET_LEAK` / `JUSTIFIED_STORAGE` / `NON_TARGET`
- показать, что итоговый submission — это осознанный release choice, а не dump всех positives из exploratory запусков
