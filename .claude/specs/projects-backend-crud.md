# Spec: Projects Backend CRUD

## Цель

Добавить CRUD-эндпоинты для ручного управления проектами пользователя. До этого был только `POST /projects/save` для массового сохранения проектов, распарсенных из CV. Теперь пользователь может вручную добавлять, редактировать и удалять отдельные проекты через UI.

## Архитектура хранения

- Хранилище — Qdrant, коллекция `projects` (см. [backend/app/storage/repository/qdrant.py:127-134](../../backend/app/storage/repository/qdrant.py)).
- SQL-таблицы для проектов нет.
- ID точки — детерминированный UUID5 от `f"{user_id}:{source_id}:{name}"` (генерируется в [backend/app/services/projects.py:35-38](../../backend/app/services/projects.py)).
- Payload точки: `user_id`, `source_id`, `project_name`, `skills`, `achievements`, `technologies`, `tech_normalized`, `text`.
- Идентификатор проекта в публичном API — строка Qdrant point ID (UUID).

## Эндпоинты

Все эндпоинты под префиксом `/api/v1/projects` ([backend/app/api/v1/api.py:27-31](../../backend/app/api/v1/api.py)). Все требуют `Authorization: Bearer <jwt>`; middleware валидирует токен и кладёт email в `request.state.user_email` ([backend/app/middleware/auth.py](../../backend/app/middleware/auth.py)).

Эндпоинты определены в [backend/app/api/v1/endpoints/projects.py](../../backend/app/api/v1/endpoints/projects.py), используют helper `_get_current_user(request, user_repo)` для разрешения текущего пользователя (404 если не найден).

### POST /api/v1/projects/save (batch-импорт)

Существующий, без изменений. Используется фронтендом для массового создания.

**Request body** (`SaveProjectsRequest`):
```json
{
  "source_id": "manual-1715000000000",
  "projects": [
    {
      "name": "LOKALI APP",
      "skills": ["проектирование REST API", "..."],
      "achievements": ["Создал REST API...", "..."],
      "technologies": ["Node.js", "MySQL", "..."]
    }
  ]
}
```

`source_id` — произвольная строка, идентифицирующая «источник» (пакет добавленных проектов). UI генерирует `manual-${Date.now()}` для ручных импортов; при импорте из CV — берётся из CV. Если по этому `source_id` уже есть точки — они **удаляются** перед записью новых (см. `ProjectStorageService.save_projects`, [backend/app/services/projects.py:53](../../backend/app/services/projects.py)).

**Response** (`SaveProjectsResponse`):
```json
{"saved": 1}
```

### GET /api/v1/projects/ (список)

**Новый.** Возвращает все проекты текущего пользователя (Qdrant scroll с фильтром `user_id`, лимит 10000).

**Response** (`ListProjectsResponse`):
```json
{
  "projects": [
    {
      "id": "9f7a3c2e-...-...",
      "source_id": "manual-1715000000000",
      "name": "LOKALI APP",
      "skills": ["..."],
      "achievements": ["..."],
      "technologies": ["..."]
    }
  ]
}
```

### PUT /api/v1/projects/{project_id} (редактирование одного)

**Новый.** Заменяет поля проекта по ID. Проверяется владелец — `payload.user_id == current_user.id`; иначе 404.

После обновления пересчитывается эмбеддинг и `text`, перезаписывается `tech_normalized`. `user_id` и `source_id` сохраняются из существующей точки.

**Request body** (`UpdateProjectRequest`):
```json
{
  "name": "LOKALI APP v2",
  "skills": ["..."],
  "achievements": ["..."],
  "technologies": ["..."]
}
```

**Response** (`ProjectResponse`) — обновлённая запись, тот же `id` и `source_id`.

**Ошибки:** `404 {"detail": "Project not found"}` если ID не существует или принадлежит другому пользователю.

### DELETE /api/v1/projects/{project_id} (удаление одного)

**Новый.** Удаляет точку из Qdrant по ID. Проверка владельца аналогично PUT.

**Response:**
```json
{"success": true, "message": "Project <id> deleted successfully"}
```

**Ошибки:** `404 {"detail": "Project not found"}`.

## Изменения по файлам

| Файл | Что добавлено |
|---|---|
| [backend/app/storage/repository/qdrant.py](../../backend/app/storage/repository/qdrant.py) | `list_by_user_id(user_id)`, `get_point_by_id(point_id)`, `delete_by_point_id(point_id)`. Импорт `PointIdsList`. |
| [backend/app/services/projects.py](../../backend/app/services/projects.py) | `ProjectStorageService.list_user_projects`, `update_project`, `delete_project`. `LookupError` для отсутствующих/чужих ID. |
| [backend/app/api/dto/projects.py](../../backend/app/api/dto/projects.py) | `ProjectResponse`, `ListProjectsResponse`, `UpdateProjectRequest`. |
| [backend/app/api/v1/endpoints/projects.py](../../backend/app/api/v1/endpoints/projects.py) | Новые routes: `GET /`, `PUT /{project_id}`, `DELETE /{project_id}`. |

## Безопасность

- Все мутирующие операции (PUT/DELETE) и листинг (GET) фильтруют/проверяют по `user_id` из JWT. Невозможно прочитать/изменить чужой проект.
- `POST /save` берёт `user_id` из текущего пользователя, не из body.

## Verification

```bash
# 1. Логин
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}' | jq -r .access_token)

# 2. Batch save
curl -X POST http://localhost:8000/api/v1/projects/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_id":"manual-test","projects":[{"name":"LOKALI APP","skills":["проектирование REST API"],"achievements":["Создал REST API"],"technologies":["Node.js","MySQL"]}]}'
# → {"saved": 1}

# 3. List
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/projects/
# → {"projects":[{"id":"...", ...}]}

# 4. Update
PID=<id из списка>
curl -X PUT "http://localhost:8000/api/v1/projects/$PID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"LOKALI APP v2","skills":[],"achievements":[],"technologies":["Go"]}'

# 5. Delete
curl -X DELETE "http://localhost:8000/api/v1/projects/$PID" \
  -H "Authorization: Bearer $TOKEN"
# → {"success":true,"message":"..."}

# 6. 404 на чужой/несуществующий
curl -X DELETE "http://localhost:8000/api/v1/projects/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer $TOKEN" -i
# → HTTP/1.1 404
```
