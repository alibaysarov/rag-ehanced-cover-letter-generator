# Фразы и графовый конструктор шаблонов сопроводительных писем

Статус: спецификация для реализации. Дата: 2026-09-21.

## 1. Цель

Заменить жёстко заданные `OPENINGS`, `BRIDGES`, `PROJECT_LEADS` и `CLOSINGS` в `backend/app/services/template_cover_letter.py` на управляемые из UI фразы и шаблоны.

После изменения путь генерации должен выглядеть так:

```text
ParsingJob.generation_mode == "template"
  -> загрузить вакансию и проекты её владельца
  -> вычислить TemplateCase
  -> выбрать активный CoverLetterTemplate с этим case
  -> пройти один допустимый путь по графу
  -> подставить только разрешённые данные
  -> сохранить письмо и метаданные шаблона
```

Ветка `generation_mode == "ai"` не меняется. При ошибке шаблона нельзя незаметно переключаться на ИИ.

## 2. Термины и границы модели

### 2.1. Фраза

`LetterPhrase` — переиспользуемая запись с `type` и `text`. Фраза не знает о своих соседях и не хранит `next`.

### 2.2. Шаблон

`CoverLetterTemplate` — метаданные шаблона и ориентированный ациклический граф (DAG):

- обычный узел `phrase` ссылается на одну `LetterPhrase`;
- служебный узел `projects` не ссылается на фразу и обозначает точное место вставки блока проектов;
- ребро хранит разрешённый переход между двумя узлами этого шаблона;
- массив `next` из исходной идеи равен списку `target_node_id` исходящих рёбер;
- позиция узла на canvas принадлежит шаблону, а не фразе.

Это не linked list: у узла может быть несколько `next`, поэтому модель является графом вариантов. Внутри одного сгенерированного письма обходится только один путь.

### 2.3. Владение

В первой версии фразы и шаблоны принадлежат конкретному `User`. Все CRUD-запросы фильтруются по `user_id`; чужой ID возвращает `404`, а не `403`. Общая админская библиотека шаблонов в эту версию не входит.

## 3. Выбор `case`

### 3.1. Enum

```python
class TemplateCase(str, Enum):
    NO_PORTFOLIO = "no_portfolio"
    RELEVANT_DOMAIN = "relevant_domain"
    PARTIAL_MATCH = "partial_match"
    NO_RELEVANT_PROJECTS = "no_relevant_projects"
```

Значения в select:

| API value | Надпись | Точное условие |
| --- | --- | --- |
| `no_portfolio` | «Портфолио пусто» | У пользователя нет ни одного пригодного проекта |
| `relevant_domain` | «Есть релевантная сфера» | Хотя бы один проект имеет не менее двух различных технологий, найденных в названии/тексте вакансии |
| `partial_match` | «Частичное совпадение» | Есть релевантный проект, но у лучшего проекта найдена ровно одна технология |
| `no_relevant_projects` | «Проекты есть, но релевантных нет» | Портфолио не пусто, но ни одна технология проектов не найдена в вакансии |

Так два похожих исходных случая разведены: `no_portfolio` означает отсутствие проектов вообще, а `no_relevant_projects` — наличие портфолио без совпадений.

### 3.2. Детерминированная классификация

Классификатор не вызывает LLM или embeddings:

1. Загрузить все проекты через `ProjectRepository.get_by_user(user_id)`.
2. Убрать проекты с пустым после trim именем. Если список пуст, вернуть `no_portfolio`.
3. Сопоставить уникальные технологии каждого проекта с `job_title + "\n" + job_text` по правилам `matching_technologies` из текущего сервиса: case-insensitive, с границами технических имён, без substring-коллизии `Java`/`JavaScript`.
4. Отсортировать проекты по `match_count DESC, project.id ASC`.
5. Если лучший `match_count == 0`, вернуть `no_relevant_projects`.
6. Если лучший `match_count == 1`, вернуть `partial_match`.
7. Если лучший `match_count >= 2`, вернуть `relevant_domain`.

Пустые технологии и дубли не учитываются. Ошибка БД не равна «нет совпадений»: её нужно пробросить и завершить генерацию со статусом `failed`. Текущее поглощение исключений в `get_projects_by_vacancy_text()` для этого пути нужно убрать.

### 3.3. Служебный узел `projects`

`projects` — отдельный `node_kind`, а не фраза и не значение `LetterPhraseType`. Он нужен backend, чтобы знать, в каком месте готового письма вывести 1–3 проекта. В UI узел показывается как нередактируемая карточка `Проекты` с бейджем `[[projects]]`.

В одном шаблоне может быть не более одного узла `projects`. Если узла нет, шаблон всё равно можно сохранить и активировать, но только после явного подтверждения:

> В вашем письме не будут указываться проекты, так как вы не указали, где хотите их вставить. Продолжить?

Если узел есть, но не лежит на каждом возможном пути, текст предупреждения другой: `В некоторых вариантах письма проекты не будут указаны. Продолжить?`

Кнопки: `Вернуться` и `Продолжить без проектов`. Подтверждение передаётся в API как `confirm_without_projects: true`; одного клиентского modal недостаточно. Для `no_portfolio` подтверждение не нужно: проектов заведомо нет, а служебный узел для этого `case` запрещён.

Для `no_relevant_projects` узел выводит до трёх первых проектов по `id`; текст шаблона не должен называть их релевантными. Для `partial_match` и `relevant_domain` выводятся до трёх проектов с `match_count > 0` в порядке из §3.2.

## 4. Фразы и подстановки

### 4.1. Типы фраз

```python
class LetterPhraseType(str, Enum):
    OPENING = "opening"
    EXPERIENCE_BRIDGE = "experience_bridge"
    PORTFOLIO_INTRO = "portfolio_intro"
    STACK_SUMMARY = "stack_summary"
    CLOSING = "closing"
    CUSTOM = "custom"
```

Enum общий для backend и frontend. Произвольные строки в `type` запрещены. `custom` позволяет добавить нестандартный блок без расширения enum.

### 4.2. Разрешённые токены

В тексте фразы допустимы:

| Токен | Значение |
| --- | --- |
| `[[job_title]]` | Название вакансии |
| `[[company_name]]` | Компания, если она известна |
| `[[projects]]` | Готовый многострочный блок из 1–3 проектов; в UI это служебный узел, а не ручной текст фразы |
| `[[matched_technologies]]` | Найденные технологии через запятую |

Это простые токены, а не Jinja/Python-выражения. Рендерер не исполняет код. Неизвестный токен даёт `422` при сохранении фразы. Пустое значение удаляет токен и лишний пробел; оставшаяся пунктуация не должна образовывать пустую строку.

Ограничения:

- `[[job_title]]`, `[[company_name]]` и `[[matched_technologies]]` можно вставить в текст любой фразы;
- `[[projects]]` запрещён в `LetterPhrase.text`: его единственное каноническое представление — служебный узел `projects`; это делает проверку наличия проектов однозначной;
- фраза после trim и подстановки не может быть пустой.

В textarea каждый допустимый токен показан как кликабельный badge: клик вставляет токен в позицию курсора. В preview текста и на карточке React Flow токены подсвечиваются отдельным цветом, но остаются plain text.

### 4.3. Источник `company_name`

Сейчас в `AutoParsedJob` нет поля работодателя. Для токена `[[company_name]]` нужно добавить nullable `company_name` в `auto_parsed_jobs`, API schemas и результат парсеров. Если сайт не вернул компанию, значение токена — пустая строка. `web_site` не использовать как имя компании.

## 5. Хранение в БД

Имена модулей могут быть уточнены при реализации, но границы сущностей обязательны.

### 5.1. `letter_phrases`

| Поле | Тип | Правила |
| --- | --- | --- |
| `id` | bigint PK | Серверный ID |
| `user_id` | FK users, index | `NOT NULL`, `ON DELETE CASCADE` |
| `type` | varchar(40) | `NOT NULL`, CHECK по `LetterPhraseType` |
| `text` | text | `NOT NULL`, 1–2000 символов после trim |
| `is_active` | bool | `NOT NULL DEFAULT true` |
| `created_at`, `updated_at` | timestamptz | UTC |

Индекс: `(user_id, type, is_active)`. Дубли текста допустимы: две одинаковые фразы могут иметь разный жизненный цикл.

### 5.2. `cover_letter_templates`

| Поле | Тип | Правила |
| --- | --- | --- |
| `id` | bigint PK | Серверный ID |
| `user_id` | FK users, index | `NOT NULL`, `ON DELETE CASCADE` |
| `name` | varchar(120) | `NOT NULL`, 1–120 символов |
| `template_case` | varchar(40) | API-алиас `case`, CHECK по `TemplateCase` |
| `status` | varchar(20) | `draft`, `active` или `archived` |
| `root_node_id` | UUID, nullable FK | Обязателен для `active` |
| `version` | int | Начинается с 1, увеличивается при изменении |
| `created_at`, `updated_at` | timestamptz | UTC |

На один `user_id + template_case` может быть ровно один `active`-шаблон. Это фиксируется partial unique index, а не только service-проверкой. Вариативность писем задаётся ветвлениями внутри графа, поэтому приоритеты между несколькими активными шаблонами не нужны.

### 5.3. `cover_letter_template_nodes`

| Поле | Тип | Правила |
| --- | --- | --- |
| `id` | UUID PK | Генерируется frontend или backend |
| `template_id` | FK templates, index | `NOT NULL`, `ON DELETE CASCADE` |
| `node_kind` | varchar(20) | `phrase` или `projects` |
| `phrase_id` | nullable FK phrases, index | Для `phrase` — `NOT NULL`, для `projects` — `NULL`; `ON DELETE RESTRICT` |
| `position_x`, `position_y` | float | Координаты React Flow, не влияют на генерацию |

Одну фразу можно добавить в один шаблон несколько раз, поэтому `next` всегда ссылается на ID узла, а не на `phrase_id`. CHECK constraint обязан зафиксировать пару `(node_kind, phrase_id)`. Partial unique index на `(template_id) WHERE node_kind = 'projects'` не даёт добавить два служебных узла.

### 5.4. `cover_letter_template_edges`

| Поле | Тип | Правила |
| --- | --- | --- |
| `id` | UUID PK | Стабильный ID для React Flow |
| `template_id` | FK templates, index | `NOT NULL`, `ON DELETE CASCADE` |
| `source_node_id` | FK nodes | `NOT NULL`, `ON DELETE CASCADE` |
| `target_node_id` | FK nodes | `NOT NULL`, `ON DELETE CASCADE` |
| `branch_order` | int | `>= 0`, порядок веток |

Ограничения: unique `(template_id, source_node_id, target_node_id)` и unique `(source_node_id, branch_order)`. Оба узла ребра обязаны принадлежать тому же `template_id`; это дополнительно проверяет service.

### 5.5. Метаданные сгенерированного письма

В `auto_parsed_jobs` добавить nullable-поля:

```text
cover_letter_template_id       bigint FK templates ON DELETE SET NULL
cover_letter_template_case     varchar(40)
cover_letter_template_version  integer
cover_letter_template_path     jsonb  # массив UUID узлов в порядке обхода
```

Также в `auto_parsed_jobs` добавить nullable `company_name` из §4.3.

Они заполняются только для успешной шаблонной генерации. При AI-генерации они `NULL`. Версия и путь нужны для отладки; текст письма остаётся каноническим снимком результата.

## 6. Инварианты графа

Черновик можно сохранить только при соблюдении базовых правил: ID уникальны, ссылки существуют, нет self-loop и нет чужих фраз. Активация и preview требуют полной валидности:

1. Есть хотя бы один узел и ровно один `root_node_id`.
2. Root принадлежит этому шаблону и не имеет входящих рёбер.
3. В графе нет циклов.
4. Все узлы достижимы из root; изолированные узлы запрещены.
5. Из каждого узла достижим хотя бы один terminal-узел без исходящих рёбер.
6. Все `phrase_id` принадлежат владельцу шаблона; inactive-фразы не допускаются в `active`-шаблоне.
7. Для `phrase` задан `phrase_id`, для `projects` он `null`; служебный узел не повторяется и запрещён для `no_portfolio`.
8. Отсутствие `projects` на всех путях не является ошибкой графа, но требует `confirm_without_projects` по §3.3.
9. Размер не превышает 100 узлов и 300 рёбер.

Порядок типов не зашивается: именно рёбра определяют, какие сочетания имеют смысл. Повтор типа или одной фразы технически разрешён.

При нарушении вернуть `422` с машиночитаемыми ошибками, например:

```json
{
  "detail": {
    "code": "invalid_template_graph",
    "errors": [
      {"code": "cycle_detected", "node_ids": ["...", "..."]},
      {"code": "unreachable_node", "node_id": "..."}
    ]
  }
}
```

## 7. HTTP API

Все endpoint находятся под `/api/v1`, требуют текущего пользователя и не принимают `user_id` из body/query.

### 7.1. CRUD фраз

```http
GET    /letter-phrases?q=&type=&is_active=&page=1&page_size=20
POST   /letter-phrases
GET    /letter-phrases/{phrase_id}
PATCH  /letter-phrases/{phrase_id}
DELETE /letter-phrases/{phrase_id}
```

`q` ищет case-insensitive substring в `text`; `type` — точный enum-фильтр. `page_size`: 1–100. Сортировка: `updated_at DESC, id DESC`.

```json
// POST/PATCH request
{
  "type": "opening",
  "text": "Добрый день! Меня заинтересовала вакансия [[job_title]].",
  "is_active": true
}

// response
{
  "id": 17,
  "type": "opening",
  "text": "Добрый день! Меня заинтересовала вакансия [[job_title]].",
  "is_active": true,
  "used_in_templates": 2,
  "created_at": "2026-09-21T10:00:00Z",
  "updated_at": "2026-09-21T10:00:00Z"
}
```

Список возвращает `{items, page, page_size, total}`. Удаление фразы, используемой хотя бы в одном узле, даёт `409 phrase_in_use` с массивом `template_ids`. Деактивация фразы из active-шаблона также даёт `409`; сначала нужно заменить узел или архивировать шаблон.

Изменение текста фразы меняет все ссылающиеся на неё шаблоны. Backend показывает этот impact через `used_in_templates`, повторно валидирует затронутые active-шаблоны и в одной транзакции увеличивает их `version`. Если новый текст делает active-шаблон невалидным, ответ `409 active_template_would_be_invalid` без частичных изменений.

### 7.2. CRUD шаблонов

```http
GET    /cover-letter-templates?q=&case=&status=&page=1&page_size=20
POST   /cover-letter-templates
GET    /cover-letter-templates/{template_id}
PUT    /cover-letter-templates/{template_id}
DELETE /cover-letter-templates/{template_id}
POST   /cover-letter-templates/{template_id}/activate
POST   /cover-letter-templates/{template_id}/preview
```

List endpoint возвращает метаданные, `has_projects_node`, `nodes_count`/`edges_count`, но не весь граф. `q` ищет case-insensitive substring в `name`; `case` и `status` — точные enum-фильтры. Detail endpoint возвращает граф целиком.

Создание и полная замена графа используют один контракт:

```json
{
  "name": "Частичное совпадение",
  "case": "partial_match",
  "version": 3,
  "confirm_without_projects": false,
  "root_node_id": "18bdd68a-f01b-4e36-a7f1-65271877df58",
  "nodes": [
    {
      "id": "18bdd68a-f01b-4e36-a7f1-65271877df58",
      "node_kind": "phrase",
      "phrase_id": 17,
      "position": {"x": 80, "y": 120}
    },
    {
      "id": "cc9bf89d-b832-42a2-96a8-aa7105615342",
      "node_kind": "projects",
      "phrase_id": null,
      "position": {"x": 420, "y": 120}
    }
  ],
  "edges": [
    {
      "id": "6945ee25-539f-4aa2-ac7c-1ad0e19e0557",
      "source_node_id": "18bdd68a-f01b-4e36-a7f1-65271877df58",
      "target_node_id": "cc9bf89d-b832-42a2-96a8-aa7105615342",
      "branch_order": 0
    }
  ]
}
```

В create/update request для phrase-узла передаётся только `phrase_id`. В detail/preview response backend дополнительно возвращает в узле read-only `phrase: {id, type, text, is_active, used_in_templates}`, чтобы frontend не делал N+1 запросов. Для projects-узла `phrase` равен `null`. Поле `phrase` из request игнорировать нельзя — extra fields должны давать `422`.

`confirm_without_projects` — командный флаг конкретного save/activate, он не хранится в БД. Если проекты могут отсутствовать в готовом письме и флаг не передан, backend возвращает:

```json
{
  "detail": {
    "code": "projects_node_confirmation_required",
    "reason": "missing_projects_node"
  }
}
```

`reason` равен `missing_projects_node` или `projects_node_not_on_all_paths`. Frontend показывает соответствующий confirmation modal и повторяет тот же запрос с `confirm_without_projects: true`. Для `no_portfolio` флаг игнорируется.

Для `POST` поле `version` не передаётся, новый шаблон всегда создаётся как `draft`. Для `PUT` `version` обязателен: несовпадение с текущей версией даёт `409 stale_template_version`. Backend заменяет metadata, nodes и edges в одной транзакции и увеличивает `version` на 1. Позиции React Flow также считаются изменением версии.

В API хранится только `edges`, а не одновременно `edges` и `node.next`: это исключает два противоречащих источника. Для концептуальной модели `next(node)` вычисляется из `edges.filter(edge.source_node_id == node.id)`.

`activate` принимает body `{"version": 4, "confirm_without_projects": false}`. Он в одной транзакции проверяет version, валидирует граф, архивирует прежний active-шаблон этого `case` и активирует целевой. Так не возникает момента с двумя активными шаблонами или без активного шаблона. Active-шаблон нельзя удалить: `409 active_template`; его нужно сначала заменить другим.

`preview` принимает произвольную вакансию текущего пользователя, не сохраняет письмо и не меняет статус шаблона:

```json
// request
{"vacancy_id": 812}

// response
{
  "detected_case": "partial_match",
  "template_case": "partial_match",
  "text": "Добрый день! ...",
  "node_path": ["...", "...", "..."]
}
```

На create-странице `Preview` недоступен, пока draft не сохранён и не получил server `id`. После первого save frontend заменяет URL на `/letter-constructor/templates/:id/edit`, и preview становится доступен.

Если `detected_case != template.case`, preview всё равно рендерит выбранный шаблон, но возвращает warning. Это позволяет проверить draft до активации.

### 7.3. Общие коды ошибок

| HTTP | `detail.code` | Смысл |
| --- | --- | --- |
| 404 | `phrase_not_found`, `template_not_found`, `vacancy_not_found` | Объекта нет или он чужой |
| 409 | `phrase_in_use`, `active_template`, `stale_template_version` | Конфликт состояния |
| 422 | `invalid_phrase`, `invalid_template_graph`, `projects_node_confirmation_required` | Ошибка входного контракта или требуемое подтверждение |

## 8. Алгоритм обхода и рендеринга

### 8.1. Выбор ветви

Путь должен быть детерминированным. Для текущего узла:

1. Получить исходящие рёбра по `branch_order ASC, edge.id ASC`.
2. Если рёбер нет, завершить обход.
3. Вычислить SHA-256 от UTF-8 строки `"{vacancy_id}:{template_id}:{template_version}:{node_id}"`.
4. Преобразовать первые 8 байтов в unsigned integer и взять `value % len(edges)`.
5. Перейти по выбранному ребру.

Одинаковые vacancy/template/version дают одинаковый путь независимо от процесса Python. Встроенный `hash()` не использовать.

### 8.2. Рендеринг

1. Для каждого `phrase`-узла пути загрузить текущий текст фразы и заменить разрешённые токены.
2. Для `projects`-узла сформировать готовый многострочный блок; пустой список даёт пустой блок.
3. Убрать пустые блоки.
4. Соединить блоки через `\n\n`.
5. Нормализовать более двух пустых строк подряд.
6. Непустой plain text — результат. Markdown/HTML сами по себе не исполняются.

Формат `[[projects]]` сохраняет текущее поведение:

```text
«Проект 1» — Python, FastAPI.
«Проект 2» — React, TypeScript.
```

У проекта без технологий выводится только `«Название».`. HTML из исходных данных не интерпретируется UI.

### 8.3. Выбор шаблона при генерации

```python
context = await build_template_context(vacancy, user_id)
template_case = classify_template_case(context)
template = await template_repository.get_active(user_id, template_case)
if template is None:
    raise TemplateConfigurationError("active_template_not_found", template_case)
letter, node_path = render_template(template, context, vacancy.id)
await vacancy_repository.save_generated_letter(
    vacancy.id,
    letter,
    template_id=template.id,
    template_case=template_case,
    template_version=template.version,
    template_path=node_path,
)
```

Выбор только по точному `case`. Перехода между `case` нет: письмо для пустого портфолио не должно внезапно утверждать, что проекты есть. Отсутствие active-шаблона — явная ошибка `active_template_not_found`; не применять ни AI, ни шаблон другого `case`.

Перед обходом backend повторно проверяет инварианты active-шаблона. Это защищает от повреждённых данных и обхода service-слоя.

## 9. UI

### 9.1. Маршруты и навигация

В sidebar добавить один пункт «Конструктор писем». Он ведёт на листинг шаблонов; библиотека фраз доступна второй вкладкой внутри раздела:

```text
/letter-constructor/templates
/letter-constructor/phrases
/letter-constructor/templates/new
/letter-constructor/templates/:id/edit
```

Все новые строки добавить в `i18n/locales/ru.json` и `en.json`. Маршруты обёрнуты в `PrivateRoute` и `AppShell`.

### 9.2. Листинг «Фразы»

- Таблица/карточки: `type`, сокращённый `text`, статус, `used_in_templates`, дата и действия.
- Поиск по тексту с debounce 300 ms, select по `type`, filter по активности и серверная пагинация.
- Создание/редактирование в modal или drawer. Под textarea показать разрешённые токены.
- Перед изменением используемой фразы показать, сколько шаблонов изменится.
- Кнопка Delete недоступна при `used_in_templates > 0`; backend-проверка остаётся обязательной.

### 9.3. Листинг шаблонов

- Показать `name`, локализованный `case`, наличие узла проектов, `status`, `version`, число узлов и `updated_at`.
- Фильтры по `case` и `status`; кнопки «Создать», «Редактировать», «Активировать», «Удалить».
- Для каждого `case` явно показать, есть ли active-шаблон. Отсутствие хотя бы одного показать как ошибку конфигурации.

### 9.4. Редактор графа

Использовать уже добавленный в `frontend/package.json` `@xyflow/react`.

Верхняя панель: обязательное имя, обязательный select `case`, status, «Сохранить», «Preview» и «Активировать».

Левая панель — библиотека фраз:

- поиск по `type` и `text` через `GET /letter-phrases`;
- пагинация или infinite scroll;
- drag-and-drop или кнопка «Добавить на схему» создаёт узел с UUID;
- кнопка «Новая фраза» открывает форму `text + type`; после `POST /letter-phrases` фраза сразу добавляется на canvas;
- отдельная кнопка «Добавить проекты» создаёт единственный `projects`-узел и не вызывает CRUD фраз;
- inactive-фразы не показывать по умолчанию.

Canvas:

- phrase-узел показывает type, начало text с подсветкой токенов и маркер `START`, если он root;
- projects-узел имеет отличающиеся цвет/иконку, не имеет редактируемого `text` или `type`;
- пользователь может назначить root, соединить узлы, удалить узел/ребро и переместить узел;
- новое ребро получает следующий `branch_order` для source; в side panel можно менять порядок;
- попытка создать self-loop или очевидный цикл блокируется на клиенте, но backend всё равно проверяет граф;
- ошибки backend подсвечивают соответствующие узлы/рёбра;
- клик по phrase-узлу открывает inspector с `type` и `text`; кнопка «Изменить фразу» меняет общую `LetterPhrase`, а не локальную копию, поэтому UI сначала показывает `used_in_templates` и impact-warning;
- переход со страницы при unsaved changes требует подтверждения;
- при `409 stale_template_version` не перезаписывать сервер: предложить перезагрузить версию или сохранить свою как новый draft.

Frontend может использовать React Flow `nodes`/`edges` напрямую. Адаптер должен только переименовать `source_node_id`/`target_node_id` в `source`/`target` и обратно.

## 10. Интеграция с текущей генерацией

### 10.1. Точка интеграции

Меняется только template-ветка `GenerateCoverCommandLetterHandler.handle()` в `backend/app/commands/generate_cover_letter.py`:

```text
сейчас: generate_template_cover_letter(... константы ...)
будет:  TemplateGenerationService.generate(vacancy, user_id)
```

`TemplateGenerationService` получает репозитории проектов, шаблонов и вакансий через dependency injection. Чистые `classify_template_case`, `select_path` и `render_path` не знают о SQLModel/FastAPI/Celery.

Автозапуск template-генерации, batch, SSE/WS, `cover_letter_text` и `is_generated` остаются из спецификации `specs/cover-letter-generation-modes.md`. Новые route генерации или Celery task не нужны.

### 10.2. Атомарность и гонки

Текст письма, `is_generated` и все template-метаданные сохраняются одним commit. Успешное Redis/WS-событие публикуется только после commit.

Сервис загружает active-шаблон, узлы и фразы в одной транзакционно согласованной операции и фиксирует его `id/version` до рендеринга. Параллельное редактирование может повлиять только на следующую генерацию.

## 11. Начальные данные и переход

Переход не должен ломать уже работающий режим `template`.

1. Alembic-миграция создаёт таблицы, constraints, indexes и nullable-метаданные вакансии.
2. Идемпотентный `DefaultTemplateProvisioner.ensure_for_user(user_id)` создаёт личные фразы и по одному active-шаблону для каждого `case` на основе текущих констант. Для `no_portfolio` создаётся граф без проектов.
3. Провижинер вызывается для существующих пользователей отдельной one-shot-командой деплоя, а для новых — после успешной регистрации.
4. Перед вызовом generator остаётся idempotent safety-вызов `ensure_for_user`, чтобы пережить неполный deploy. Он не восстанавливает удалённые/заменённые шаблоны после маркера `defaults_provisioned_at` у пользователя.
5. Только после заполнения дефолтов и их smoke-проверки переключить `GenerateCoverCommandLetterHandler` с констант на БД.

Данные дефолтов нужно хранить в версионируемом Python/JSON seed-файле, а не дублировать большой SQL в migration. Downgrade удаляет новые таблицы/поля, но не меняет сохранённый `cover_letter_text`.

## 12. План реализации

Пункты выполнять строго по порядку. После каждого шага сначала запустить узкие тесты, затем переходить к следующему.

### T01 — Зафиксировать backend-контракты и БД

- [ ] Создать enum-ы `TemplateCase`, `LetterPhraseType`, `TemplateNodeKind`, `TemplateStatus` в одном backend-модуле; не дублировать строки по сервисам.
- [ ] Добавить модели `LetterPhrase`, `CoverLetterTemplate`, `CoverLetterTemplateNode`, `CoverLetterTemplateEdge` в `backend/app/models/` и экспорты в `models/__init__.py`.
- [ ] Добавить в `AutoParsedJob` поля `company_name` и четыре template-metadata из §5.5.
- [ ] Создать одну Alembic migration: таблицы, FK, CHECK, unique/partial indexes и nullable-поля. Downgrade удаляет их в обратном порядке.
- [ ] Прогнать migration upgrade/downgrade/upgrade на тестовой БД.

### T02 — Сделать чистую доменную логику

- [ ] Вынести из `template_cover_letter.py` matcher технологий без изменения его текущей семантики.
- [ ] Реализовать чистые функции `classify_template_case`, `validate_graph`, `select_path`, `render_path`; они не импортируют SQLModel, FastAPI или Redis.
- [ ] `validate_graph` возвращает список structured errors и отдельно признак `paths_without_projects`; последний не смешивать с ошибками DAG.
- [ ] Написать unit-тесты до подключения к API.

### T03 — Реализовать repositories и services

- [ ] Добавить repository фраз с owner-filtering, search, filters, pagination и `used_in_templates`.
- [ ] Добавить repository шаблонов: list/detail, загрузка active-графа, full graph replacement, activation swap.
- [ ] Добавить service-слой: owner checks, валидация токенов, graph validation, `confirm_without_projects`, optimistic lock по `version`.
- [ ] Все изменения template + nodes + edges делать в одной транзакции; не вызывать `commit()` из нескольких repository внутри одной операции.

### T04 — Открыть HTTP API

- [ ] Добавить Pydantic schemas для list/detail/create/update/preview и structured errors.
- [ ] Добавить routers фраз и шаблонов в `backend/app/api/v1/endpoints/`, зарегистрировать их в `backend/app/api/v1/api.py`.
- [ ] На каждом endpoint брать current user из auth dependency; `user_id` из client payload не принимать.
- [ ] Добавить API-тесты на CRUD, filters, pagination, 404 для чужого ID, 409, 422 и version race.

### T05 — Добавить default templates до переключения generator

- [ ] Перенести текущие `OPENINGS`, `BRIDGES`, `PROJECT_LEADS`, `CLOSINGS` в версионируемый seed-файл.
- [ ] Сделать `DefaultTemplateProvisioner.ensure_for_user`: четыре active-шаблона; `no_portfolio` без projects-узла, остальные с ним.
- [ ] Добавить `defaults_provisioned_at` и идемпотентность: второй запуск не создаёт дубли.
- [ ] Вызвать provisioner после регистрации и из one-shot deployment command для существующих users.

### T06 — Подключить template generation

- [ ] Создать `TemplateGenerationService`: загрузка вакансии и всех проектов user, расчёт case, загрузка exact active template, выбор пути, render, save.
- [ ] Заменить только template-ветку в `GenerateCoverCommandLetterHandler.handle`; AI-ветку и её prompt не менять.
- [ ] Текст, `is_generated` и template-metadata сохранить одним commit. Success SSE/WS публиковать только после commit.
- [ ] Если exact active template нет или он повреждён, завершить task как `failed`; не затирать старое письмо и не вызывать AI.

### T07 — Протянуть `company_name` от parser до renderer

- [ ] Добавить optional `company_name` в vacancy DTO/schemas и в parser implementations; селектор работодателя для каждого сайта реализовать отдельно.
- [ ] Сохранять значение в `AutoParsedJob`; пустое/неизвестное значение хранить как `NULL`, а не `web_site`.
- [ ] Добавить тест парсера и render-тест для известной/неизвестной компании.

### T08 — Создать frontend data layer и list pages

- [ ] Создать `frontend/src/features/letter-constructor/` с `types.ts`, `api.ts`, `hooks.ts`, `components/`; API DTO должны точно повторять backend JSON.
- [ ] Добавить sidebar item, routes в `App.tsx`, pages и все ru/en translation keys.
- [ ] Сделать templates list: debounce search, case/status filters, server pagination, create/edit/activate/delete actions.
- [ ] Сделать phrases list: debounce search, type/active filters, pagination, create/edit/delete и impact/error dialogs.

### T09 — Создать React Flow editor

- [ ] Создать два custom node components: `PhraseNode` и `ProjectsNode`; зарегистрировать их в `nodeTypes`, объект `nodeTypes` держать вне render component.
- [ ] Сделать adapter API graph -> React Flow и React Flow -> API; не отправлять UI-only `data` в backend.
- [ ] Сделать library panel: search/filter, add existing phrase, create phrase and immediately add, add singleton projects node.
- [ ] Реализовать connect/delete/move, root selection, branch ordering, token highlighting, node inspector и backend error highlighting.
- [ ] При save сначала послать `confirm_without_projects: false`; на `projects_node_confirmation_required` показать modal по `reason` и повторить payload с `true` только после кнопки продолжения.
- [ ] Добавить preview, activate, stale-version dialog и browser/router unsaved-changes guard.

### T10 — Приёмка и порядок deploy

- [ ] Запустить backend unit/API/integration tests в `app-backend`, Pyright/lint, frontend Vitest и `npm run build`.
- [ ] Сначала deploy migration, затем выполнить one-shot provisioning, проверить по четыре active template на user, и только после этого deploy generator switch.
- [ ] Smoke-тест: четыре case, с projects-узлом/без него, пустая company, ветвление, preview, batch, single regeneration, SSE/WS.
- [ ] Отдельно smoke-проверить AI mode и убедиться, что он не читает template repositories.

## 13. Тесты

### 13.1. Backend unit

- Каждый из четырёх `case`, включая пустые имена/технологии.
- `Java`/`JavaScript`, `C++`, `C#`, `.NET`, `Node.js`, регистр и дубли.
- Одинаковый путь при одинаковом seed и распределение по веткам на наборе vacancy ID.
- Цикл, self-loop, dangling/cross-template edge, unreachable node, wrong root, duplicate branch order, invalid `(node_kind, phrase_id)`, duplicate projects-node, projects-node в `no_portfolio`, inactive/foreign phrase, limit overflow.
- `projects_node_confirmation_required`: нет узла, узел есть не на всех путях, confirmation false/true, `no_portfolio` без confirmation.
- Неизвестный токен, пустая фраза, 0/1/2/3 проекта и проект без технологий.

### 13.2. Backend API/integration

- Все CRUD-операции и owner isolation.
- Поиск, filters, pagination, `phrase_in_use`, activation swap и stale version.
- Все четыре active-шаблона созданы provisioner-ом повторно без дублей.
- Режим `template` берёт шаблон по фактическому case, а `ai` не обращается к репозиторию шаблонов.
- При отсутствии active-шаблона task завершается `failed`, старое письмо не затирается, success event не публикуется.
- Сохранённые text/template metadata принадлежат одной попытке и пишутся атомарно.

### 13.3. Frontend

- Поиск/фильтрация фраз и ошибки CRUD.
- Добавление узла, соединение, удаление, выбор root, порядок веток и round-trip API -> React Flow -> API.
- Подсветка server validation errors, stale version и unsaved-changes guard.
- Narrow viewport: библиотека фраз открывается в drawer, canvas не ломает общий layout.

## 14. Критерии готовности

- [ ] Пользователь управляет своими фразами и находит их по `type` и `text`.
- [ ] Пользователь создаёт/редактирует шаблон в `@xyflow/react`, а backend атомарно сохраняет валидный DAG.
- [ ] У каждого `case` есть ровно один active-шаблон на пользователя.
- [ ] При «Использовать шаблоны» backend детерминированно вычисляет `case` и берёт точно ему соответствующий active-шаблон.
- [ ] Все возможные пути active-графа завершаются; шаблон без гарантированного projects-узла сохраняется только после явного confirmation.
- [ ] Одинаковый контекст и версия шаблона дают одинаковый путь и текст.
- [ ] Шаблонная генерация не вызывает LLM/embeddings и не делает fallback на ИИ.
- [ ] Текущие batch, одиночная генерация, SSE/WS и AI-режим не регрессировали.

## 15. Вне задачи

- Условные рёбра с выражениями: ветвление по данным делается через `case`, а ветки внутри графа дают только текстовые варианты.
- Веса/вероятности рёбер, A/B-тесты и аналитика эффективности фраз.
- Версионный архив, из которого можно дословно восстановить старую версию; сам сохранённый текст письма не теряется.
- Общая админская библиотека и шаринг шаблонов между пользователями.
- Ручное изменение `case` уже созданной вакансии.

## 16. Зафиксированные продуктовые решения

Эти решения убирают неоднозначности для реализации:

1. `projects` — служебный узел, а не переиспользуемая фраза. Ручной `[[projects]]` в тексте фразы запрещён.
2. Отсутствие projects-узла — не ошибка, а подтверждаемое предупреждение. Backend тоже требует confirmation.
3. Граф может ветвиться. Ветка выбирается детерминированно, а не случайно.
4. Для каждого user и `case` ровно один active-шаблон; draft-шаблонов может быть несколько.
5. `relevant_domain` в MVP означает не семантическую «сферу», а два или более technology matches у лучшего проекта. LLM/embeddings для case не вызываются.
6. `company_name` берётся только из структурированного поля вакансии; если оно неизвестно, токен удаляется при render.
