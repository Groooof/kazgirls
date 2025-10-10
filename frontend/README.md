# Svinka Frontend

Этот проект, создан на Vue 3 с использованием Vite, TypeScript, Pinia, Vue Router.

## Работа с fastAPI
Если вы не работаете с fastApi то удалите папку `./src/fastApi`

Чтобы работать с fastApi у вас должен быть .env файл в котором есть базовый url

Если нужно сгенерировать файлы fastApi в консоли `make generate-api`
(обязательно зайдите в Makefile и поменяйте url откуда он будет генерироваться)

Когда генерируешь папку от fastApi могут быть проблемы с разрешением редактирования файлов в папке
для этого прописать команду ниже:
`sudo chown -R $(whoami) ./src/fastApi`

## Работа с Sentry
Чтобы работать с Sentry у вас должен быть .env файл в котором есть dsn Sentry

## Установка

```bash
npm install
```
### Для запуска в режиме разработки:
npm run dev

### Для дев-сборки:
npm run build-dev

### Для продакшн-сборки:
npm run build-prod

### Для проверки типов TypeScript:
npm run type-check

## В проекте настроены ESLint, OXLint и Prettier.

### Запуск всех линтеров и автофиксация:
npm run lint

### Проверка форматирования (без исправления):
npm run beauty:check

### Автоформатирование кода:
npm run beauty

## Перед тем, как пушить изменения в репозиторий, ОБЯЗАТЕЛЬНО запустите все линтеры и проверку типов иначе тесты не пройдут:
npm run lint
npm run type-check
npm run beauty:check
