# План: Хранение проектов в Qdrant + ранжирование по вакансии

## Контекст

`/cv-import` ([backend/app/main.py:102-118](backend/app/main.py#L102-L118)) уже парсит резюме в `CVImportModel.projects` ([backend/app/schemas/llm_outputs/cv_parse.py:5-21](backend/app/schemas/llm_outputs/cv_parse.py#L5-L21)) с полями `name / skills / achievements / technologies`, но результат отдаётся клиенту и нигде не сохраняется. `/parse` ([backend/app/main.py:124-142](backend/app/main.py#L124-L142)) парсит вакансию через `parse_hh` и возвращает `JobRequirement { name, project_name, requirements }` — но проекты пользователя никак не сопоставляются с вакансией.

Коллекция `projects` (3072-dim, COSINE) уже создаётся в [backend/app/services/pdf.py:18](backend/app/services/pdf.py#L18) и пуста — её надо начать использовать.

Цель этой итерации:
1. Хранение проектов **только в Qdrant** (без Postgres-таблицы).
2. Сохранение — **отдельным `POST`-эндпоинтом** (фронт сам решает, когда).
3. В **основной endpoint `/parse`** — добавить шаг: после `parse_hh` сделать векторный поиск по `projects` коллекции и вернуть ранжированный список проектов пользователя.

## Дизайн

### 1. Структура данных в Qdrant

**Одна точка = один проект.** Это даёт правильную гранулярность ранжирования (мы ранжируем проекты, а не подпункты). Дробить проект на отдельные точки по skill/achievement не нужно — реконструкция будет сложнее, эмбеддингов больше, а пользы для нашей задачи никакой.

**ID точки:** детерминированный `uuid5(NAMESPACE_DNS, f"{user_id}:{source_id}:{project_name}")`. Это делает `save_projects` идемпотентным: повторный вызов с теми же данными перезапишет ту же точку, а не создаст дубликат.

**Payload точки:**
```python
{
  "user_id": int,                # для фильтрации в поиске
  "source_id": str,              # привязка к CV-сессии (для cleanup)
  "project_name": str,
  "skills": list[str],
  "achievements": list[str],
  "technologies": list[str],
  "tech_normalized": list[str],  # lower().strip() — пригодится для keyword-фильтра позже
  "text": str,                   # та строка, которую эмбеддили (ключ "text" нужен, чтобы существующий QdrantStorage.search() её корректно вытаскивал — см. qdrant.py:34)
}
```

### 2. Текстовое представление для эмбеддинга

**Проект** (то, что эмбеддим в Qdrant):
```
Проект: {name}
Навыки: {", ".join(skills)}
Достижения:
- {achievement_1}
- {achievement_2}
...
Технологии: {", ".join(technologies)}
```

**Вакансия** (запрос для поиска):
```
Должность: {name}
Область проекта: {project_name}
Требования:
- {requirement_1}
- {requirement_2}
...
```

Структуры зеркальны → семантика и ключевые слова (Node.js, PostgreSQL, RabbitMQ, …) попадают в один контекст с обеих сторон. `text-embedding-3-large` хорошо ловит и русский, и английский, и кросс-язычные совпадения.

### 3. Что переиспользуем / что добавляем

**Переиспользуем:**
- [`PdfService.embed_texts()`](backend/app/services/pdf.py#L80) — единая точка эмбеддинга (через `BaseEmbedder`).
- [`QdrantStorage.upsert()`](backend/app/storage/repository/qdrant.py#L16) — без изменений.
- [`QdrantStorage(collection_name="projects", dim=3072)`](backend/app/services/pdf.py#L18) — инстанс уже создаётся.

**Расширяем `QdrantStorage`** ([backend/app/storage/repository/qdrant.py](backend/app/storage/repository/qdrant.py)):
- В `search()` добавить опциональный параметр `query_filter: Filter | None = None` и пробросить его в `client.query_points(..., query_filter=query_filter)`. Обратная совместимость — параметр по умолчанию `None`.
- Добавить фабрику `get_projects_storage() -> QdrantStorage` (синглтон через module-level переменную, по аналогии с существующей `get_vector_storage()` на строке 79).

**Добавляем:**

- `backend/app/services/projects.py` — `ProjectStorageService`:
  - `save_projects(user_id: int, source_id: str, projects: list[ProjectFromCVModel]) -> int` — собирает текст, эмбеддит батчем, делает upsert. Перед upsert вызывает `storage.delete_by_source_id(source_id)` (метод уже существует, [qdrant.py:40](backend/app/storage/repository/qdrant.py#L40)) — это гарантирует, что при повторном импорте удалённые/переименованные проекты не останутся в индексе.
  - `rank_projects(user_id: int, vacancy: JobRequirement, top_k: int = 5) -> list[dict]` — строит query text, эмбеддит, вызывает `storage.search(query_vector, top_k, query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]))`, возвращает `[{score, payload}]`.
  - Внутренние хелперы `_build_project_text(p)` и `_build_vacancy_text(v)`.

- `backend/app/api/dto/projects.py` — DTO:
  - `SaveProjectsRequest { source_id: str, projects: list[ProjectFromCVModel] }`
  - `SaveProjectsResponse { saved: int }`

- Новый endpoint `POST /api/v1/projects/save`:
  - Файл: `backend/app/api/v1/endpoints/projects.py`
  - Регистрируем в [backend/app/api/v1/api.py](backend/app/api/v1/api.py).
  - `user_id` берём через `request.state.user_email` (заполняется [AuthMiddleware:36](backend/app/middleware/auth.py#L36)) + lookup в `UserRepository` — это уже существующий паттерн в `/api/v1/*` ручках.

### 4. Изменение `/parse` (главный endpoint)

Текущий `/parse` ([main.py:124-142](backend/app/main.py#L124-L142)) висит на корне и **проходит мимо `AuthMiddleware`** (middleware защищает только `/api/v1/*` — [auth.py:21](backend/app/middleware/auth.py#L21)). Чтобы получать `user_id` для фильтрации проектов, переносим эндпоинт под `/api/v1/parse` (новый файл `backend/app/api/v1/endpoints/parse.py`, регистрируем в `api.py`). Тело и логика парсинга остаются прежними.

Новое поведение:
```python
@router.post("/parse")
async def parse(body: ParseDto, request: Request):
    user_id = _resolve_user_id(request)  # из request.state.user_email

    text = await parse_hh(body.url)
    vacancy: JobRequirement = (JobParsePrompt().prompt_template | JobParsePrompt().get_model).invoke({"job_text": text})

    ranked = projects_service.rank_projects(user_id=user_id, vacancy=vacancy, top_k=5)

    return {"result": vacancy, "body": body.url, "ranked_projects": ranked}
```

Если у пользователя ещё нет сохранённых проектов — `ranked_projects = []`, без ошибки.

### 5. Что НЕ делаем в этой итерации

- Не создаём Postgres-таблицу `projects` (по решению пользователя).
- Не делаем гибридный re-ranking (cosine + tech-overlap) — добавим, если pure-vector окажется недостаточно точным. `tech_normalized` в payload закладываем заранее, чтобы потом ничего не переэмбеддить.
- Не интегрируем ранжирование в `letter.py` — это следующая итерация.
- Не добавляем CRUD на отдельные проекты — только batch save.

## Файлы, которые меняем / создаём

| Файл | Действие |
|---|---|
| [backend/app/storage/repository/qdrant.py](backend/app/storage/repository/qdrant.py) | `search()` ← `query_filter`; `+ get_projects_storage()` |
| `backend/app/services/projects.py` | **новый** — `ProjectStorageService` |
| `backend/app/api/dto/projects.py` | **новый** — `SaveProjectsRequest`, `SaveProjectsResponse` |
| `backend/app/api/v1/endpoints/projects.py` | **новый** — `POST /projects/save` |
| `backend/app/api/v1/endpoints/parse.py` | **новый** — переносим `/parse` сюда + добавляем ranking |
| [backend/app/api/v1/api.py](backend/app/api/v1/api.py) | регистрация двух новых роутеров |
| [backend/app/main.py](backend/app/main.py) | удалить старый `/parse` (124-142) |

