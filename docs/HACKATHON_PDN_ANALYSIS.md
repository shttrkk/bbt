# Leak-Aware Problem Interpretation

## Как задача понимается в финальной версии проекта

Исходный кейс звучит как поиск персональных данных в файловом хранилище.

Финальная проектная интерпретация уже более узкая и практическая:

- наличие ПДн само по себе не равно инциденту
- риск возникает, когда ПДн хранятся вне разумного контекста
- target — suspicious / leak-like / unjustified storage

## Что считается target

Типовые target leak-классы:
- анкеты
- employee forms
- доверенности
- consent docs
- applicant docs
- handover / service / access request docs
- correspondence с персональным bundle
- subject-level exports физлиц
- фото/сканы персональных документов

## Что не должно автоматически считаться target

- публичные contact directories
- официальные contact docs
- public reports
- policies
- public disclosures
- орг-реквизиты
- blank templates

## Почему это важно

Если классифицировать всё по принципу “нашли ПДн -> positive”, система быстро захламляется:
- staff contacts
- public university/corporate docs
- declarations and reports
- legal/policy docs
- structured business/reference exports

Именно поэтому финальная версия строится вокруг:
- genre
- anchors and bundles
- sensitivity
- public/private justification
- storage context

## Практический вывод

В защите нужно объяснять, что проект решает задачу ближе к DLP / privacy risk triage, чем к naive entity spotting.
