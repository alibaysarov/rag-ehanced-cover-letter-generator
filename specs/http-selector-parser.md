# Спецификация: HTTP/Playwright-парсеры с конструктором CSS-селекторов

## 1. Цель и границы

Заменить необходимость писать JavaScript для новых «Сайтов для поиска» на
визуальный конструктор правил извлечения. Конструктор первой версии — обычные
формы, а не React Flow. Его конфигурация сохраняется в БД и позволяет получить:

1. список вакансий: `title`, `link`, `vacancy_id`;
2. данные одной вакансии: `job_title`, `job_text` (и опционально `company_name`);
3. номера страниц для пагинации.

Новые правила извлекают данные через BeautifulSoup и CSS selectors. HTML может
быть получен двумя transport-ами: `http` (`httpx`) или `playwright`.

Существующий режим с сохранёнными полями `evaluate_vacancy_list`,
`evaluate_vacancy_page`, `evaluate_pagination` **не удалять и не менять**. Он
остаётся `legacy_js + playwright` и должен вести себя идентично текущей версии.
Он нужен для уже созданных сайтов и для сложных сайтов, которые пока нельзя
описать селекторами.

Не входит в MVP:

- React Flow / произвольный DAG;
- выполнение пользовательского Python или JavaScript в новом режиме;
- автоматическое переключение HTTP -> Playwright после ошибки;
- авторизация, прокси, CAPTCHA bypass, произвольные cookies.

Последний пункт намеренный: HTTP->Playwright fallback скрывает неправильную
конфигурацию, непредсказуемо нагружает браузер и затрудняет диагностику.
Пользователь явно выбирает transport. Внутри каждого transport-а есть retry,
а внутри каждого поля — fallback по селекторам.

## 2. Термины и итоговая модель

У парсера есть две ортогональные настройки:

| Поле | Значения | Назначение |
| --- | --- | --- |
| `extraction_engine` | `legacy_js`, `selectors_v1` | Как превращать HTML/DOM в данные. |
| `fetch_mode` | `playwright`, `http` | Как получить HTML. |

Допустимые комбинации в MVP:

| Engine | Fetch mode | Поддержка |
| --- | --- | --- |
| `legacy_js` | `playwright` | Полностью поддержан; это текущий код. |
| `legacy_js` | `http` | Запрещён схемой. JS выполняется через `page.evaluate`. |
| `selectors_v1` | `http` | Основной новый сценарий. `httpx` получает HTML, BeautifulSoup извлекает поля. |
| `selectors_v1` | `playwright` | Поддержан. Playwright ждёт/скроллит страницу, берётся `page.content()`, после чего те же правила применяются BeautifulSoup. |

Это означает: выбор `playwright` не означает, что новый конструктор хранит JS.
Он лишь нужен, чтобы получить финальный DOM для SPA/динамических сайтов. Сами
селекторы и правила одинаковы в обоих transport-ах.

## 3. Текущее состояние, которое нельзя сломать

- `Parser` и Pydantic `ParserWrite` хранят три обязательные JS-строки.
- `ConfiguredVacancyParser` наследует `GeneralVacancyParser` и вызывает JS через
  `page.evaluate`.
- `parse_site` сейчас всегда поднимает browser.
- `SiteParseService` удерживает существующую параллельность: список страниц
  грузится через `asyncio.gather`, карточки одной вакансии обрабатываются с
  семафором `4`.
- Парсер-снимок (`parser_snapshot`) уже фиксируется в `parsing_site_jobs`; это
  обязательно сохранить, иначе изменения сайта в UI повлияют на уже начатую
  задачу.

В результате рефакторинга `SiteParseService` должен сохранить семафор, лимит
вакансий, дедупликацию, запись результатов и события. Меняется только способ
получить список/детали.

## 4. Данные в PostgreSQL

### 4.1. Миграция

Создать новую Alembic-миграцию от текущей head
`o2d3e4f5a6b7_cover_letter_template_graph.py`. Не переписывать старую миграцию
`l9a0b1c2d3e4_user_managed_parsers.py`.

В таблицу `parsers` добавить:

```sql
ALTER TABLE parsers
  ADD COLUMN extraction_engine VARCHAR(32) NOT NULL DEFAULT 'legacy_js',
  ADD COLUMN fetch_mode VARCHAR(32) NOT NULL DEFAULT 'playwright',
  ADD COLUMN request_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN extraction_config JSONB NULL;

ALTER TABLE parsers ADD CONSTRAINT ck_parsers_extraction_engine
  CHECK (extraction_engine IN ('legacy_js', 'selectors_v1'));
ALTER TABLE parsers ADD CONSTRAINT ck_parsers_fetch_mode
  CHECK (fetch_mode IN ('http', 'playwright'));
ALTER TABLE parsers ADD CONSTRAINT ck_parsers_engine_transport
  CHECK (extraction_engine <> 'legacy_js' OR fetch_mode = 'playwright');
ALTER TABLE parsers ADD CONSTRAINT ck_parsers_selector_config
  CHECK (
    (extraction_engine = 'legacy_js' AND extraction_config IS NULL)
    OR
    (extraction_engine = 'selectors_v1' AND extraction_config IS NOT NULL)
  );
```

В Alembic использовать `postgresql.JSONB(astext_type=sa.Text())`, как в
существующей таблице. У всех старых записей значения по default остаются
`legacy_js` и `playwright`; JS-поля не менять и не переносить.

`request_config` даже для legacy хранит `{}`: так схема проста, а пользователь
позже сможет настроить selector-режим без следующей миграции. В БД не хранить
секреты, cookies сессии или пароли.

Добавить в `backend/app/models/parser.py` одноимённые поля:

```python
extraction_engine: str = Field(default="legacy_js", max_length=32, nullable=False)
fetch_mode: str = Field(default="playwright", max_length=32, nullable=False)
request_config: dict[str, Any] = Field(
    default_factory=dict, sa_column=Column(JSONB, nullable=False)
)
extraction_config: dict[str, Any] | None = Field(
    default=None, sa_column=Column(JSONB, nullable=True)
)
```

Никаких отдельных таблиц `selectors`, `nodes` или `fields` в MVP не создавать.
Конфигурация целиком является одной версионируемой атомарной настройкой парсера;
JSONB даёт снимку задачи ровно те же данные. Отдельные таблицы усложнят
обновление, каскады и version-conflict без выгоды для фиксированных трёх стадий.

### 4.2. Формат `request_config`

```json
{
  "headers": {
    "Accept-Language": "ru-RU,ru;q=0.9"
  },
  "timeout_seconds": 20,
  "max_retries": 3,
  "retry_base_delay_seconds": 0.5,
  "playwright": {
    "wait_for_selector": "main",
    "wait_until": "domcontentloaded",
    "scroll_to_bottom": true,
    "post_load_delay_ms": 500
  }
}
```

Ограничения Pydantic:

- `headers`: не более 20 строк; ключ/значение не пустые; запретить `Host`,
  `Content-Length`, `Connection`, `Cookie`, `Authorization`, `Proxy-*`;
- `timeout_seconds`: 1..60, по умолчанию 20;
- `max_retries`: 0..3, по умолчанию 2 или 3;
- `retry_base_delay_seconds`: 0.1..5;
- `wait_for_selector`: CSS selector до 1 000 символов, только при Playwright;
- `wait_until`: один из `domcontentloaded`, `load`, `networkidle`; default
  `domcontentloaded`;
- `post_load_delay_ms`: 0..5 000;
- стандартный User-Agent задаёт сервер, не пользователь. Заголовки пользователя
  лишь дополняют whitelist.

### 4.3. Формат `extraction_config`

Схема всегда versioned. Это позволяет позже добавить nodes/React Flow как
`selectors_v2`, не ломая сохранённые парсеры.

```json
{
  "schema_version": 1,
  "list": {
    "item_selector": "[data-qa='vacancy-serp__vacancy']",
    "fields": {
      "title": {
        "source": {
          "kind": "selector",
          "selectors": [
            "[data-qa='serp-item__title-text']",
            "h2 a"
          ],
          "extract": "text"
        },
        "required": true,
        "normalize": {"strip": true, "collapse_whitespace": true}
      },
      "link": {
        "source": {
          "kind": "selector",
          "selectors": ["a[data-qa='serp-item__title']", "a"],
          "extract": "attribute",
          "attribute": "href",
          "absolute_url": true
        },
        "required": true,
        "normalize": {"strip": true}
      },
      "vacancy_id": {
        "source": {"kind": "field", "field": "link"},
        "transforms": [
          {"kind": "regex", "pattern": "/vacancy/(\\d+)", "group": 1}
        ],
        "required": true,
        "normalize": {"strip": true}
      }
    }
  },
  "detail": {
    "fields": {
      "job_title": {
        "source": {
          "kind": "selector",
          "selectors": ["h1", "[data-qa='vacancy-title']"],
          "extract": "text"
        },
        "required": true,
        "normalize": {"strip": true, "collapse_whitespace": true}
      },
      "job_text": {
        "source": {
          "kind": "selector",
          "selectors": ["[data-qa='vacancy-description']", "article", "main"],
          "extract": "text"
        },
        "required": true,
        "normalize": {"strip": true, "collapse_whitespace": true}
      },
      "company_name": {
        "source": {
          "kind": "selector",
          "selectors": ["[data-qa='vacancy-company-name']"],
          "extract": "text"
        },
        "required": false,
        "normalize": {"strip": true, "collapse_whitespace": true}
      }
    }
  },
  "pagination": {
    "enabled": true,
    "selectors": ["[data-qa='pager-page']", ".pagination a"],
    "extract": "text",
    "transforms": [
      {"kind": "regex", "pattern": "\\d+", "group": 0}
    ]
  }
}
```

Смысл fallback:

- список `selectors` — упорядоченный fallback: используется первый selector,
  который нашёл элемент с непустрым итоговым значением;
- `job_text` может последним selector-ом иметь `main` или `body`, но UI должен
  предупреждать, что такой fallback часто захватывает меню/футер;
- для `list.item_selector` fallback не нужен в MVP: одна корневая карточка
  задаёт контекст. Если потребуется, v2 добавит `item_selectors: []`;
- для pagination объединить элементы всех selector-ов, удалить дубли и
  игнорировать нечисловые значения.

### 4.4. Типизированные сущности и валидация

Не принимать произвольный `dict` в API. Описать Pydantic-модели (в
`backend/app/schemas/parser.py` или в новом `parser_config.py`):

- `FetchMode = Literal['http', 'playwright']`;
- `ExtractionEngine = Literal['legacy_js', 'selectors_v1']`;
- `RequestConfig`, `PlaywrightRequestConfig`;
- `SelectorSource(kind='selector', selectors, extract, attribute?, absolute_url)`;
- `FieldSource(kind='field', field)`;
- discriminated union `ExtractionSource`;
- `RegexTransform(kind='regex', pattern, group=0)`;
- `TextNormalize`;
- `FieldRule`;
- `ListExtractionConfig`, `DetailExtractionConfig`, `PaginationExtractionConfig`;
- `SelectorExtractionConfig(schema_version=1, list, detail, pagination?)`.

Правила валидации:

1. Поддерживать только CSS selectors (`Tag.select`, SoupSieve); не добавлять
   XPath и JS.
2. При сохранении компилировать каждый selector через SoupSieve/`BeautifulSoup`
   на пустом документе; вернуть validation error с путём поля, если синтаксис
   неверен.
3. Максимум: selector 1 000 символов, 5 fallback selectors на поле, 20
   selectors на всю конфигурацию, regex 500 символов. Не допускать пустых
   строк и regex, не компилирующихся Python `re`.
4. В `list.fields` разрешены и обязательны ровно `title`, `link`,
   `vacancy_id`; в `detail.fields` обязательны `job_title`, `job_text`,
   `company_name` опционален.
5. `attribute` обязателен только для `extract='attribute'`, запрещён иначе;
   допустимый атрибут — непустая строка до 128 символов.
6. `absolute_url=true` имеет смысл только для `attribute=href`; использовать
   `urljoin(page_url, value)` на backend.
7. Источник `field` может ссылаться только на поле текущей стадии. В list
   поддержать ссылку `vacancy_id -> link`; проверить отсутствие циклов
   topological-sort-ом. Для detail field-to-field в v1 не нужен.
8. `pagination` обязателен и `enabled=true`, когда `has_pagination=true`;
   при `has_pagination=false` должен быть `null` или `enabled=false`.
9. Совместимость engine: `legacy_js` требует все прежние JS-строки и
   `fetch_mode='playwright'`; `selectors_v1` требует `extraction_config`.

`ParserWrite`, `ParserCreate`, `ParserUpdate`, `ParserSnapshot` и
`ParserDetail` должны включать новые поля. Для обратной совместимости входа
старого UI API в период выката можно на Pydantic уровне дать defaults:
`extraction_engine='legacy_js'`, `fetch_mode='playwright'`,
`request_config={}`, `extraction_config=None`.

## 5. Runtime backend

### 5.1. Общий контракт

Убрать из `SiteParseService` зависимость от конкретного `Browser` и от
`GeneralVacancyParser`. Ввести небольшой runtime-протокол, например:

```python
class VacancyParserRuntime(Protocol):
    async def get_list(self, text: str, job_id: int) -> list[Vacancy]: ...
    async def parse_single_vacancy(self, vacancy_id: str) -> SingleVacancy: ...
    async def aclose(self) -> None: ...
```

`SiteParseService.run` принимает runtime. Он сохраняет текущую логику:

- вызывается `get_list`;
- дедупликация/`vacancy_limit`/`record_found` остаются без изменения;
- создаются конкурентные detail-задачи;
- существующий semaphore 4 остаётся (вынести в константу);
- каждая detail-задача вызывает `runtime.parse_single_vacancy`, сохраняет
  результат и учитывает частичные ошибки так же, как сейчас;
- `aclose()` вызывается один раз в `finally` внешнего task.

Не передавать одну BS4-сущность между задачами. Каждая HTTP/Playwright загрузка
возвращает собственный HTML, а `BeautifulSoup` создаётся локально.

### 5.2. Legacy Playwright runtime

Выделить текущий путь в `LegacyPlaywrightParserRuntime`:

- внутри использует существующий `ConfiguredVacancyParser`;
- сохраняет `page.evaluate`, `scroll_page_bottom`, `secure_request_route`,
  timeout и retry `GeneralVacancyParser`;
- Browser/context/pages управляются внутри runtime либо через аккуратно
  переданный factory;
- результат, порядок и пределы остаются прежними.

Не переписывать сами старые JS-константы и не пытаться интерпретировать legacy
JS через BS4.

### 5.3. Selector runtime и fetchers

Создать изолированные модули, например:

```text
backend/app/services/scraper/
  extraction/selectors.py          # чистый BS4 extractor, без сети
  extraction/models.py             # внутренние typed results при необходимости
  fetchers/base.py                 # FetchedPage(url, html), PageFetcher protocol
  fetchers/http.py                 # HttpxPageFetcher
  fetchers/playwright.py           # PlaywrightPageFetcher
  parsers/selector_runtime.py      # URL format + list/detail/pagination orchestration
  parsers/runtime_registry.py      # выбирает runtime по snapshot
```

`PageFetcher.fetch(url) -> FetchedPage` обязан вернуть final URL после redirect
и HTML. Relative links всегда резолвить от `FetchedPage.url`, а не от
`base_url`, чтобы корректно работать с redirect.

#### HTTPX

- Использовать один `httpx.AsyncClient` на runtime/site task:
  `follow_redirects=True`, заданный timeout, ограниченный connection pool.
- Передавать безопасные default headers + допустимые пользовательские headers.
- Выполнять асинхронные запросы; блокирующий `httpx.Client` из `main.py`
  использовать только как пример, в production не копировать.
- На ответах `2xx` вернуть `response.text`; 3xx обрабатываются httpx;
  `4xx` (кроме 408/429) не повторять; 408, 429, 500, 502, 503, 504 и сетевые
  `httpx.TimeoutException`/`httpx.TransportError` повторять.
- Exponential backoff с jitter: `base * 2^attempt + random(0, 0.25)`, не
  превышать 5 секунд; уважать разумный `Retry-After` для 429, максимум 10 с.
- Ограничить тело ответа, например 5 MiB по `Content-Length` и streaming;
  не парсить binary/mime type не `text/html`/`application/xhtml+xml`.

#### Playwright для `selectors_v1`

- Использовать текущий `pw_browser(headless=True)` и `secure_request_route`.
- На страницу: `goto(url, wait_until=config.wait_until)`, при настройке
  `wait_for_selector` вызвать `page.wait_for_selector`, при включённом флаге
  выполнить `scroll_page_bottom`, затем `wait_for_timeout(post_load_delay_ms)`.
- Получить `html = await page.content()` и `final_url = page.url`; дальше
  вызвать тот же чистый BS4 extractor.
- List pages могут оставаться параллельными, каждый fetch получает свою page;
  detail pages ограничены тем же semaphore 4.
- Повторять временные timeout/navigation errors по той же политике попыток.
  Не retry-ить ошибку extraction: неверный selector не станет правильным от
  следующего запроса.

### 5.4. Чистый selector extractor

`selectors.py` не знает о FastAPI, Celery, Browser или HTTP. Он получает
`html`, `page_url`, типизированную конфигурацию и возвращает результат либо
контекстную ошибку.

Алгоритм списка:

1. `soup = BeautifulSoup(html, 'html.parser')`.
2. Выполнить `soup.select(list.item_selector)`; если карточек нет —
   `ExtractionError(stage='list', code='items_not_found')`.
3. Для каждой card извлечь `title`, `link`, затем `vacancy_id` (с учётом
   зависимостей полей), нормализовать значения.
4. Карточка без любого `required` поля пропускается и учитывается в warning;
   не падать из-за одной испорченной карточки.
5. Если после фильтрации нет ни одной валидной вакансии — stage error с
   количеством пропусков. Ограничить до существующего `MAX_RESULT_CARDS`.
6. Провалидировать конечные `Vacancy(name=title, link=link, vacancy_id=id)`.

Алгоритм detail:

1. Извлечь `job_title`, `job_text`, опционально `company_name` от `soup`.
2. Fallback selector-ы пробуются последовательно, затем применяются
   transforms/normalization.
3. Непустой `job_text` обязателен, как и в текущем parser-е. Пустой или
   отсутствующий `job_title` — ошибка, так как schema требует оба поля.
4. Вернуть `SingleVacancy(..., job_url=page_url)`.

Алгоритм pagination:

1. Если `has_pagination=false`, вернуть `1` и не обращаться к config.
2. Собрать тексты/атрибуты всех configured elements.
3. Применить regex transforms, оставить уникальные положительные integers.
4. Если валидных чисел нет, вернуть `1`; иначе `min(max(numbers), max_pages)`.
5. URL каждой страницы продолжает строиться через существующий `format_url` и
   `{page}`. Если при `has_pagination=true` URL не использует `{page}`,
   Pydantic отклоняет конфигурацию, как и сейчас.

В сообщениях ошибок указывать только stage, selector path и короткую причину;
не писать в БД HTML, заголовки или запрос пользователя.

### 5.5. Параллельность и отказоустойчивость

Сохранить текущую архитектуру, не сериализовать HTTP:

```text
list page 1 ─┐
list page 2 ─┼─ asyncio.gather ─► объединение/дедупликация вакансий
list page N ─┘
                              │
                     semaphore(4)
              ┌───────────────┼───────────────┐
detail #1     detail #2       ...           detail #N
```

Нужно сделать fetch semaphore отдельной константой, например
`MAX_CONCURRENT_DETAIL_REQUESTS = 4`, и применить его одинаково к HTTP и
Playwright. Для list pages можно ввести отдельный безопасный лимит 4–5 вместо
безграничного gather; это сохраняет параллельность, но не создаёт до 50
одновременных соединений при `max_pages=50`.

Политика ошибок:

- ошибка pagination/list после исчерпания retry завершает site job с ошибкой,
  как сейчас;
- ошибка одной detail-вакансии не отменяет другие detail-задачи; увеличить
  failure counter и завершить site как failed, если были failures;
- selector fallback применяется к отсутствующему элементу, пустому text и
  отсутствующему attribute; это не network retry;
- не retry-ить `ValidationError`, `ExtractionError`, запрещённый URL и HTTP
  400/401/403/404/410 (кроме будущей явной настройки);
- сохранять текущий `SITE_PARSE_DEADLINE_SECONDS = 15 * 60` как общий deadline;
  при timeout всегда закрыть AsyncClient/browser/context/pages.

## 6. Изменения task и registry

1. `runtime_registry.create_runtime(snapshot)` валидирует
   `ParserSnapshot.model_validate(snapshot)` и выбирает implementation по
   `extraction_engine`/`fetch_mode`.
2. В `backend/app/tasks/parse_site.py` не открывать `pw_browser` безусловно.
   Создать runtime; legacy/selectors+playwright открывают browser только когда
   он нужен, selectors+http — не запускает Chromium вовсе.
3. В `finally` гарантированно вызвать `await runtime.aclose()`.
4. Изменить сигнатуру `SiteParseService.run`, чтобы browser исчез из публичного
   API. Его unit tests обновить на fake runtime, а не на Playwright.
5. Снимок `parser_snapshot` уже создаётся из `ParserSnapshot`; после расширения
   схемы новые поля автоматически попадут в Redis catalog и job snapshot.
   Проверить это тестом явно.
6. Одиночный URL в `VacancyScrapingService.parse_single` также должен выбирать
   runtime по snapshot. Для `selectors_v1 + http` он не должен обращаться к
   global Chromium. Если домен не имеет parser-а, оставляем существующий
   fallback извлечения body Playwright, это другая функция и не часть этой
   миграции.

## 7. API

CRUD `/api/v1/parsers` остаётся тем же URL. Добавить поля в request/response:

```ts
type ExtractionEngine = 'legacy_js' | 'selectors_v1';
type FetchMode = 'http' | 'playwright';

interface ParserInput {
  // существующие URL, pagination, JS-поля и format_url
  extraction_engine: ExtractionEngine;
  fetch_mode: FetchMode;
  request_config: RequestConfig;
  extraction_config: SelectorExtractionConfig | null;
}
```

Создать отдельный endpoint проверки, не сохраняющий парсер:

```text
POST /api/v1/parsers/preview
```

Он принимает `ParserWrite` и один из payload-ов:

```json
{ "stage": "list", "search_text": "Python", "page": 0 }
{ "stage": "detail", "url": "https://site.example/vacancy/123" }
{ "stage": "pagination", "search_text": "Python" }
```

Проверки preview:

- detail `url` обязан быть абсолютным HTTP(S), без credentials, и иметь тот же
  hostname, что `base_url`; запретить SSRF в localhost, private/link-local IP,
  IPv6 loopback и redirect на них;
- list/pagination строят URL только через уже валидный `format_url`;
- у endpoint маленький rate limit per user и строгий deadline (например 30 с);
- возвращать максимум 10 list items и предупреждения по пропущенным карточкам;
- не сохранять parser, `parser_usage` или preview HTML;
- response: `resolved_url`, `fetch_mode`, `stage`, `result`, `warnings`,
  `timing_ms`; при ошибке 422 для config, 502/504 с структурированным stage code
  для fetch/extraction.

Preview использует тот же fetcher/extractor, не копию логики. Для legacy
preview можно пока либо выполнить существующий JS через Playwright, либо явно
не показывать кнопку preview в legacy UI; предпочтительно поддержать и его,
чтобы тестовая поверхность была одинаковой.

## 8. Frontend: обычные блоки, не node graph

Изменения в `frontend/src/features/search-sites/ParserForm.tsx`, `types.ts`,
`api.ts` и переводах `i18n/locales/{ru,en}.json`.

### 8.1. Верх формы

Сохранить блоки из текущего screenshot без изменений по смыслу:

- Название;
- URL поиска (`base_url`);
- Шаблон URL вакансии (`single_url`);
- URL-шаблон и query параметры;
- pagination start / max pages.

Под ними добавить `Способ загрузки страницы`:

- radio/select: `HTTP (быстрее)` и `Playwright (для JavaScript-сайтов)`;
- default для новых selector parser-ов: `HTTP`;
- возле Playwright показать подсказку: «Страница рендерится в браузере, затем
  данные извлекаются по CSS-селекторам».

И `Способ извлечения`:

- «Конструктор селекторов (рекомендуется)» — `selectors_v1`;
- «JavaScript, legacy» — `legacy_js`.

При выборе legacy автоматически выбрать Playwright, скрыть новые конструкторы
и показать существующие три textarea без изменения их названий/значений. Не
удалять JS из state при переключении режима: пользователь может передумать.
При выборе constructor показать три блока ниже; textarea JS можно скрыть, но
значения сохранять в объекте для API/backward compatibility.

### 8.2. Блок «Получить список вакансий»

Поля:

1. `CSS selector карточки вакансии` (`item_selector`), required.
2. Таблица фиксированных полей: `title`, `link`, `vacancy_id`.
3. Для `title` и `link`: список fallback selectors. Каждая строка имеет input
   selector и кнопки `+ fallback` / удалить. Для link дополнительно выбор
   `Текст` / `HTML` / `Атрибут`; по default `Атрибут href`; checkbox
   «Преобразовать в абсолютный URL» включён.
4. Для `vacancy_id`: radio «Из CSS selector» / «Из другого поля». При выборе
   второго показать select `link` и optional «Регулярное выражение» + группа
   (default `1`).
5. Чекбоксы нормализации: trim и collapse whitespace (по умолчанию включены).

На старте создать удобные пустые defaults: `title`/`link` required, id source
из link, regex пустой. Перед сохранением форма не делает вид, что regex уже
работает — она должна потребовать либо заполненный id selector, либо regex.

### 8.3. Блок «Получить данные одной вакансии»

Показать отдельные карточки:

- `job_title` — обязательное поле, selector fallback list, extract text;
- `job_text` — обязательное поле, selector fallback list, extract text;
- `company_name` — опциональный; кнопку «Добавить название компании».

Не давать пользователю переименовывать системные выходные поля: backend
контракт фиксирован.

### 8.4. Блок «Получить номера страниц»

Показывать только если включён чекбокс pagination. Поля:

- один или несколько CSS fallback selectors элементов пагинации;
- extract `text` или `attribute`;
- regex для извлечения числа, default `\\d+`, group `0`;
- текст: «Если номера не найдены, будет обработана только первая страница».

Существующий `has_pagination`, `pagination_start`, `max_pages` и URL query
`{page}` остаются источником адресов страниц; конструктор получает лишь
число страниц.

### 8.5. Preview и состояния

У каждого из трёх selector-блоков разместить кнопку `Проверить`. Она вызывает
`/parsers/preview` с текущим несохранённым состоянием формы.

- Для списка/pagination дать поле «Тестовый запрос», предзаполненное последним
  значением в локальном state, например `Python`.
- Для detail — поле URL тестовой вакансии, либо ссылка из последнего успешного
  list-preview.
- Показывать spinner, resolved URL, transport, время, первые десять объектов
  или найденные номера.
- Warnings о пропущенных карточках показывать как warning alert.
- Ошибку показать у конкретного блока: `Не найден selector ...`, `HTTP 403`,
  `id не извлечён regex ...`. Не отображать stack trace.

Не внедрять DOM inspector в этой задаче. Его можно добавить позднее как
следующий UX-шаг; конфигурационный формат менять для него не потребуется.

### 8.6. Типы и UX-совместимость

- Расширить `ParserInput` новыми типизированными объектами; не использовать
  `any`.
- Обновить `emptyParser`: для нового создания поставить
  `selectors_v1`, `http`, базовый `request_config`, валидный по форме skeleton
  `extraction_config`. Если backend требует заполненных selectors, кнопку Save
  блокировать/показывать validation до отправки.
- Для загруженных старых parser-ов API вернёт `legacy_js + playwright`, и форма
  должна сразу открыть старую UI-ветку со всеми прежними JS textarea.
- При редактировании уже запущенного parser-а сохранить существующее сообщение
  `editInUse` и optimistic version conflict.
- Добавить RU и EN строки, не хардкодить русский новый текст в компоненте.

## 9. Безопасность

1. Новый selector engine не выполняет пользовательский JS, XPath или template
   expressions.
2. Ограничить URL и каждый redirect от SSRF: только `http/https`, без userinfo,
   DNS/IP проверка перед подключением, блок private/loopback/link-local/
   multicast/reserved networks. Нельзя полагаться только на hostname validation
   из текущей `normalize_site_key`.
3. Для production HTTP клиент должен иметь лимиты на response size, redirects,
   connect/read/write/pool timeouts и список безопасных headers.
4. Не логировать cookies, authorization headers, полный HTML или query с
   возможными персональными данными. Логировать parser id, site key, stage,
   status, attempt, время.
5. CSS selector limits и regex length защищают от чрезмерно дорогих правил;
   выполнение extractor-а также обернуть stage timeout-ом.
6. Preview выполняет сетевое обращение от имени сервера, поэтому имеет те же
   SSRF правила, rate limit и размер ответа, что production parsing.

## 10. План реализации для GPT-5.5

### Навыки и рабочие правила

Перед работой GPT-5.5 должен:

1. Прочитать `AGENTS.md` в корне репозитория.
2. Для любых backend test/lint/migration команд использовать навык
   `docker-backend`: прочитать его `SKILL.md` полностью и следовать ему.
   Он определяет, как запускать Python внутри `app-backend` Docker-контейнера.
3. Не нужен ни `imagegen`, ни Google Drive skill, ни plugin installation.
4. Использовать `apply_patch` для исходников и миграций; не затрагивать
   неотносящиеся пользовательские изменения.

### Инкременты (делать в этом порядке)

1. **Схемы и миграция.** Добавить DB columns/model/Pydantic unions/validators.
   Добавить migration от `o2d3e4f5a6b7`, проверить upgrade и rollback на
   пустой БД. Существующие parser-и обязаны после migration пройти
   `ParserSnapshot.model_validate` без правок.
2. **Чистое ядро extraction.** Покрыть тестами `selectors.py` на fixtures HTML
   прежде, чем соединять с сетью. Реализовать relative selector, fallback,
   attribute, `urljoin`, regex, normalization, list/detail/pagination и
   структурированные ошибки.
3. **HTTP fetcher.** Реализовать async httpx-client, retry policy, size/URL
   limits и корректное закрытие. Unit-тесты с `httpx.MockTransport`, без реального
   доступа в интернет.
4. **Selector runtime.** Соединить fetcher, существующий URL formatter,
   extractor и runtime contract. Сначала `selectors_v1 + http`; затем
   `selectors_v1 + playwright` через `page.content()`.
5. **Refactor orchestration.** Вынести legacy путь в runtime adapter. Переделать
   `SiteParseService`, `parse_site`, registry и single URL parsing. Сохранить
   4 одновременных detail задачи, добавить контролируемый list semaphore.
6. **API preview.** Вынести общий service, добавить endpoint и его security
   validations. Он не должен иметь собственную логику selector parsing.
7. **Frontend.** Расширить types/API, построить mode switch и три формы,
   подключить preview, переводы и ошибки. Не добавлять React Flow.
8. **Регрессия и cleanup.** Прогнать тесты, type check, migration на свежей
   БД. Не удалять legacy JS-поля, классы или UI.

Не объединять это в один большой не проверенный diff. После каждого инкремента
запускать узкие тесты; migration и runtime refactor лучше выделить в отдельные
коммиты.

## 11. Тестовый план и критерии приёмки

### Backend unit tests

Добавить/расширить тесты для:

- schema: legacy defaults; запрещён `legacy_js + http`; selectors config
  requires three list fields/two detail fields; invalid CSS/regex; cycles;
  pagination invariants;
- extractor: CSS fallback, whitespace, missing optional field, missing
  required field, relative href, id-from-link regex, invalid cards filtering,
  empty valid list, pagination de-dup/max limit;
- HTTP fetcher: redirects, retryable/non-retryable statuses, exhausted retry,
  closing client, response size/type;
- selector runtime: list pages execute concurrently within configured limit;
  detail requests execute concurrently but never above 4; one detail error does
  not cancel other saves;
- runtime registry: historical snapshot chooses `LegacyPlaywrightParserRuntime`,
  selector HTTP does not request a browser, selector Playwright does;
- parser catalog/job snapshot: new JSON config is preserved byte-for-byte in
  Redis serialization and `parsing_site_jobs.parser_snapshot`;
- preview: no database mutation, max 10 output items, domain/SSRF validation,
  structured extraction errors.

Existing `test_parser_registry.py`, `test_parser_catalog.py`,
`test_site_parse_service.py`, `test_vacancy_limit.py` особенно важны: обновить
их, но не ослаблять assertions ради прохождения теста.

### Frontend checks

- Создание selector HTTP parser-а отправляет ожидаемый typed JSON.
- Открытие historical legacy parser-а отображает JS textarea и не показывает
  selector config как обязательный.
- Переключение legacy включает Playwright; обратное переключение не уничтожает
  введённый JS.
- Pagination block следует за checkbox; Save не отправляется при невалидных
  mandatory selector fields.
- Preview верно показывает loading/result/error и не требует сохранения формы.
- `npm run build` проходит.

### Команды проверки

Выполнять через инструкции навыка `docker-backend`:

```text
cd backend && uv run python -m unittest discover -s tests
cd backend && make lint
cd frontend && npm run build
```

Если Docker-навык предписывает другой wrapper/контейнер, использовать именно
его. В финальном отчёте GPT-5.5 перечисляет реально выполненные команды и их
результаты, а также отдельно отмечает всё, что невозможно проверить локально.

### Acceptance criteria

Фича готова, только если одновременно верно следующее:

1. Старый parser с JS из БД продолжает запускаться Playwright и выдаёт прежний
   результат без ручного редактирования.
2. Новый parser можно создать без JS, выбрав HTTP и заполнив три UI-блока.
3. Новый HTTP parser выполняет поиск списка, pagination и detail parsing через
   `httpx + BeautifulSoup`; Chromium при этом не запускается.
4. Selector parser с выбранным Playwright получает DOM браузером, но извлекает
   те же поля тем же selector engine.
5. Fallback selectors и сетевой retry работают согласно разделу 5.5.
6. List и details остаются параллельными с ограничением конкурентности; один
   сбой detail не отменяет все остальные.
7. Parser snapshot сохраняет transport и extraction config, поэтому изменения
   UI не меняют уже стартовавшую задачу.
8. Preview использует production code path и безопасно диагностирует правило до
   сохранения.
