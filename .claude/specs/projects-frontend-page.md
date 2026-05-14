# Spec: Projects Frontend Page

## Цель

Страница `/projects` с CRUD-управлением проектами пользователя:
- список проектов (карточки),
- batch-добавление нескольких проектов одним диалогом,
- редактирование одного проекта,
- удаление с подтверждением,
- анимированные list-инпуты для полей-массивов `skills` / `achievements` / `technologies`.

## Стек

- React 19 + TypeScript, Chakra UI 2 (UI), React Query 5 (data), axios (`authApi`, Bearer-токен подставляется автоматически), framer-motion (анимации), react-router-dom 7. Всё уже в [frontend/package.json](../../frontend/package.json).

## Файлы

| Файл | Назначение |
|---|---|
| [frontend/src/components/AnimatedListInput.tsx](../../frontend/src/components/AnimatedListInput.tsx) | Переиспользуемый input для массива строк с framer-motion-анимацией. |
| [frontend/src/components/ProjectFormCard.tsx](../../frontend/src/components/ProjectFormCard.tsx) | Форма одного проекта (name + 3 × AnimatedListInput). Тип `ProjectInput`, `emptyProject()`. |
| [frontend/src/pages/ProjectsPage.tsx](../../frontend/src/pages/ProjectsPage.tsx) | Страница `/projects`: список, batch-add modal, edit modal, delete confirm. Содержит хуки `useProjects`, `useSaveProjects`, `useUpdateProject`, `useDeleteProject`. |
| [frontend/src/App.tsx](../../frontend/src/App.tsx) | Новый маршрут `<Route path="/projects" element={<PrivateRoute><ProjectsPage/></PrivateRoute>} />`. |
| [frontend/src/features/auth/components/Navigation.tsx](../../frontend/src/features/auth/components/Navigation.tsx) | Ссылки «Резюме» (`/my-cvs`) и «Проекты» (`/projects`) в шапке. |

## Контракт `AnimatedListInput`

```ts
interface AnimatedListInputProps {
  label: string;
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}
```

- Локально хранит массив `{id, value}[]` — id генерируется через `crypto.randomUUID()` (fallback на `Math.random`), чтобы `key` в React был стабильным при удалении строк.
- При изменении пропа `values` извне (если массив новый) — синхронизирует локальное состояние (сравнение со ссылкой `lastEmitted`).
- Анимация:
  - вход: `initial={{opacity:0, x:-20, height:0}}` → `animate={{opacity:1, x:0, height:'auto'}}`
  - выход: `exit={{opacity:0, x:20, height:0}}` (через `AnimatePresence`)
  - `transition={{duration:0.2}}`, `overflow:'hidden'` на обёртке.
- Кнопка «Добавить» добавляет пустую строку в конец, на каждой строке — `IconButton` с `DeleteIcon`.

## Контракт `ProjectFormCard`

```ts
interface ProjectInput {
  name: string;
  skills: string[];
  achievements: string[];
  technologies: string[];
}

interface ProjectFormCardProps {
  value: ProjectInput;
  onChange: (next: ProjectInput) => void;
  onRemove?: () => void;   // если есть — рисуется кнопка «×» в углу
  index?: number;          // номер карточки в batch-режиме
  nameError?: string;
}
```

Внутри — Chakra `Card` с обязательным `Input` для `name` и тремя `AnimatedListInput` для каждого массива.

## API-хуки (внутри ProjectsPage.tsx)

`PROJECTS_QUERY_KEY = ['projects']`. Все мутации делают `queryClient.invalidateQueries({queryKey: PROJECTS_QUERY_KEY})` в `onSuccess`.

| Hook | Метод | Path | Body / Response |
|---|---|---|---|
| `useProjects()` | GET | `/projects/` | → `{projects: ProjectResponse[]}` |
| `useSaveProjects()` | POST | `/projects/save` | `{source_id, projects: ProjectInput[]}` → `{saved: number}` |
| `useUpdateProject()` | PUT | `/projects/{id}` | `ProjectInput` (без id) → `ProjectResponse` |
| `useDeleteProject()` | DELETE | `/projects/{id}` | → `{success, message}` |

Клиент — `authApi` из [frontend/src/api/client.ts](../../frontend/src/api/client.ts) (axios с Bearer-токеном).

## UI / поведение

### Layout страницы

- Сверху — `Navigation` (шапка), кнопка «Сгенерировать письмо» (переход на `/`), кнопка «Добавить проекты» (открыть batch modal).
- Заголовок «Мои проекты», описание.
- Сетка карточек (`SimpleGrid columns={{base:1, md:2}}`).
- Состояния: `Spinner` при загрузке, красная карточка при ошибке, пустой стейт когда `projects.length === 0`.

### Карточка проекта

- Имя как `Heading`, кнопки `Edit`/`Delete` (`IconButton ghost`) в шапке.
- Тело: `technologies` и `skills` как `Badge` в `Wrap`, `achievements` — буллет-список.
- Анимация появления/исчезновения карточек через `AnimatePresence` + `motion.div` (`scale: 0.95 → 1`).

### Batch-add modal

- Размер `3xl`, `scrollBehavior="inside"`.
- Список `ProjectFormCard` с локальным состоянием `{id, data}[]` (id — уникальный для key).
- Кнопка «+ Ещё проект» (под списком) добавляет пустую карточку с анимацией (`motion.div` с `height: 0 → auto`).
- Кнопка «×» в карточке (включается только если карточек > 1) — удаляет с анимацией.
- Submit: валидирует, что у каждой карточки `name.trim() !== ''`; иначе показывает `nameError` для конкретной карточки.
- Перед отправкой пустые строки в массивах фильтруются (`cleanProject`).
- `source_id` генерируется как `manual-${Date.now()}`.

### Edit modal

- Размер `2xl`. Один `ProjectFormCard`, прединициализированный значениями из выбранного проекта.
- Submit → `useUpdateProject.mutate({id, data})`.

### Delete confirm

- Chakra `AlertDialog` (паттерн из [UserCVPage.tsx:573-605](../../frontend/src/pages/UserCVPage.tsx)).
- Submit → `useDeleteProject.mutate(id)`.

## Маршрут и навигация

- `/projects` обёрнут в `PrivateRoute` — без логина редирект на `/login`.
- В `Navigation` две ссылки (`Button as={RouterLink}`): «Резюме» → `/my-cvs`, «Проекты» → `/projects`.

## Verification

```bash
cd frontend && npm run dev
# Открыть http://localhost:5173/projects (после логина)
```

1. Открыть batch-add modal → видна одна пустая карточка.
2. Нажать «Ещё проект» — вторая карточка появляется с slide-in.
3. В скиллах первой карточки нажать «Добавить» 3 раза → 3 инпута появляются с slide-in. Удалить второй → slide-out.
4. Очистить `name` первой карточки → submit показывает ошибку под полем.
5. Заполнить обе карточки → submit → toast «Сохранено: 2», карточки появляются в сетке с анимацией.
6. Edit одной карточки → изменить name, добавить технологию, сохранить → карточка обновилась.
7. Delete → confirm-dialog → карточка исчезает с анимацией.
8. Reload `/projects` — данные подтянулись из бэка.
9. Logout → переход на `/projects` редиректит на `/login`.
