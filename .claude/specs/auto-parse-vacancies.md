# Spec: Auto-Parsing Vacancies from hh.ru

**Feature branch:** `feature/auto-parse-vacancies`  
**Status:** Planning  
**Date:** 2026-05-17

---

## 1. Overview

User enters a job title → backend searches hh.ru, scrapes multiple pages of results in parallel → fetches full text of each unique vacancy → streams progress back to client via SSE → client displays parsed vacancies in a list with a detail modal.

---

## 2. Database Models

### `parsing_jobs` table

Tracks a single parsing session. Persists across page reloads.

```
id            INTEGER PK
user_id       INTEGER FK → users.id
query         TEXT               — raw search string
status        TEXT               — pending | running | done | failed
total_found   INTEGER DEFAULT 0  — total vacancy IDs collected from list pages
saved_count   INTEGER DEFAULT 0  — how many detail pages saved so far
error         TEXT NULLABLE
created_at    DATETIME
finished_at   DATETIME NULLABLE
```

SQLModel file: `backend/app/models/parsing_job.py`

---

### `auto_parsed_jobs` table

One row per vacancy saved.

```
id              INTEGER PK
user_id         INTEGER FK → users.id
parsing_job_id  INTEGER FK → parsing_jobs.id
vacancy_id      TEXT        — hh.ru numeric ID (e.g. "133086215")
url             TEXT        — https://hh.ru/vacancy/<id>
job_title       TEXT        — title extracted from vacancy page
job_text        TEXT        — full text of vacancy
created_at      DATETIME
```

SQLModel file: `backend/app/models/auto_parsed_job.py`

Add these models to `backend/app/models/__init__.py` so Alembic picks them up.

---

## 3. Alembic Migrations

Two new files in `backend/alembic/versions/`:

1. `xxxx_create_parsing_jobs_table.py`
2. `xxxx_create_auto_parsed_jobs_table.py`

Run order: parsing_jobs first (auto_parsed_jobs has FK to it).

---

## 4. Backend — Scraper Service

**File:** `backend/app/services/scraper/hh_scraper.py`

### 4.1 URL Template

```python
LIST_URL = "https://hh.ru/search/vacancy?text={query}&area=1&page={page}"
VACANCY_URL = "https://hh.ru/vacancy/{vacancy_id}"
```

Use `urllib.parse.quote_plus` to encode the query string.

### 4.2 Resource Blocking

Block images and fonts to reduce RAM and speed up scraping:

```python
async def _block_resources(route, request):
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()
```

Apply via `page.route("**/*", _block_resources)`.

### 4.3 Phase 1 — List Page Scraping

**Concurrency:** `asyncio.Semaphore(3)` — 3 pages in parallel  
**One browser instance** shared across all list-page coroutines (new `page` per coroutine).

For each page:
1. Navigate to `LIST_URL` with query + page number.
2. Extract vacancy card elements.
3. For each card:
   - If card contains text "Вы уже откликнулись" → **skip**.
   - Otherwise extract `vacancyId` from `href` of the button with `data-qa="vacancy-serp__vacancy_response"`.
4. Detect total pages: look for the last pagination item or use `found` count in the page header.
5. Return list of vacancy IDs from this page.
6. **Delay:** after each page, sleep `random.uniform(1, 5)` seconds before releasing the semaphore — reduces bot-detection risk on hh.ru.

```python
import random
await asyncio.sleep(random.uniform(1, 5))
```

**HTML selectors:**
```
Vacancy card:       [data-qa="vacancy-serp__vacancy"]
Already responded:  check if card contains text "Вы уже откликнулись"
Response button:    a[data-qa="vacancy-serp__vacancy_response"]
Vacancy ID:         parse `vacancyId=(\d+)` from button href
Pagination total:   [data-qa="pager-page"]:last-child  or parse from total count text
```

**Max pages:** 5 (configurable via env `HH_MAX_PAGES`, default 5).

### 4.4 Phase 2 — Vacancy Detail Scraping

**Concurrency:** `asyncio.Semaphore(4)` — 4 vacancies in parallel  
**Worker pool pattern:** split vacancy ID list into chunks of 4, process with `asyncio.gather`.

For each vacancy ID:
1. Navigate to `VACANCY_URL`.
2. Extract title: `[data-qa="vacancy-title"]` → `.inner_text()`
3. Extract body: `[data-qa="vacancy-description"]` → `.inner_text()`
4. Save row to `auto_parsed_jobs`.
5. Increment `parsing_jobs.saved_count` (atomic update via DB).
6. Emit SSE event with current `saved_count`.

### 4.5 Single Browser Lifecycle

```python
async def run_parse_job(job_id: int, query: str, user_id: int, db: Session):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            await _phase1_collect_ids(browser, query, job_id, db)
            await _phase2_fetch_details(browser, job_id, user_id, db)
        finally:
            await browser.close()
```

One browser → one parse session. No shared state between different users' jobs.

### 4.6 SSE Progress Broadcasting

Use an in-memory dict of `asyncio.Queue` objects keyed by `job_id`:

```python
_progress_queues: dict[int, asyncio.Queue] = {}
```

After each vacancy save, put a progress event into the queue. SSE endpoint reads from the queue and streams to client.

---

## 5. Backend — API Endpoints

**Router file:** `backend/app/services/scraper/auto_parse_router.py`  
**Mounted at:** `/api/v1/auto-parse` in `backend/app/api/v1/api.py`

### `POST /api/v1/auto-parse/start`

```json
Request:  { "query": "php разработчик" }
Response: { "parsing_job_id": 42 }
```

- Create `parsing_job` row with `status="pending"`.
- Launch `run_parse_job(...)` as background task via `asyncio.create_task`.
- Return `parsing_job_id` immediately.

### `GET /api/v1/auto-parse/status/{parsing_job_id}`

```json
{
  "id": 42,
  "query": "php разработчик",
  "status": "running",
  "saved_count": 17,
  "total_found": 45,
  "created_at": "...",
  "finished_at": null
}
```

### `GET /api/v1/auto-parse/jobs/{parsing_job_id}/vacancies`

Returns list of `auto_parsed_jobs` for this job (pagination optional).

```json
[
  {
    "id": 1,
    "vacancy_id": "133086215",
    "url": "https://hh.ru/vacancy/133086215",
    "job_title": "PHP Developer",
    "job_text": "Требования: ...",
    "created_at": "..."
  }
]
```

### `GET /api/v1/auto-parse/history`

Returns all `parsing_jobs` for the current user, newest first.

### `GET /api/v1/auto-parse/stream/{parsing_job_id}`

Server-Sent Events endpoint. Returns `text/event-stream`.

```
data: {"saved_count": 5, "total_found": 45, "status": "running"}

data: {"saved_count": 6, "total_found": 45, "status": "running"}

data: {"saved_count": 45, "total_found": 45, "status": "done"}
```

Stream closes when `status` becomes `done` or `failed`.

---

## 6. Frontend

### 6.1 New Route

`/auto-parse` → `frontend/src/pages/AutoParsePage.tsx`

Add to `App.tsx`:
```tsx
<Route path="/auto-parse" element={<PrivateRoute><AppShell><AutoParsePage /></AppShell></PrivateRoute>} />
```

Add to `Sidebar.tsx` `navItems` array:
```tsx
{ to: '/auto-parse', icon: IconSearch, label: t('nav.autoParse') }
```

Add translation keys to `en.json` and `ru.json`.

### 6.2 API Client

**File:** `frontend/src/features/auto-parse/api/auto-parse-client.ts`

```ts
startParse(query: string): Promise<{ parsing_job_id: number }>
getStatus(jobId: number): Promise<ParsingJob>
getVacancies(jobId: number): Promise<AutoParsedJob[]>
getHistory(): Promise<ParsingJob[]>
createEventSource(jobId: number): EventSource   // /stream/{jobId}
```

### 6.3 Types

**File:** `frontend/src/features/auto-parse/types/index.ts`

```ts
type ParsingJobStatus = 'pending' | 'running' | 'done' | 'failed';

interface ParsingJob {
  id: number;
  query: string;
  status: ParsingJobStatus;
  saved_count: number;
  total_found: number;
  created_at: string;
  finished_at: string | null;
}

interface AutoParsedJob {
  id: number;
  vacancy_id: string;
  url: string;
  job_title: string;
  job_text: string;
  created_at: string;
}
```

### 6.4 Hook

**File:** `frontend/src/features/auto-parse/hooks/useAutoParse.ts`

Manages:
- `startParse(query)` → POST → store `jobId`
- Subscribe to SSE → update `progress` state
- Fetch vacancies list (on done or periodically)
- Restore state from `localStorage` (persist `jobId` across page reloads)

### 6.5 Page Layout — `AutoParsePage.tsx`

```
┌────────────────────────────────────────────────────┐
│  Авто Парсинг                                       │
│                                                     │
│  ┌──────────────────────────────┐  ┌─────────────┐ │
│  │  Название вакансии...        │  │  Парсить    │ │
│  └──────────────────────────────┘  └─────────────┘ │
│                                                     │
│  [Progress bar: 17 / 45 сохранено]  status: running│
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  PHP Developer                               │  │
│  │  Требования: Laravel, MySQL...               │  │
│  │  hh.ru/vacancy/133086215          [Открыть] │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  ...                                         │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

**Components:**
- `ParseSearchBar` — input + button, disabled while `status === 'running'`
- `ParseProgressBar` — Chakra `Progress`, shows `saved_count / total_found`, hidden when `status === 'pending'`
- `VacancyCard` — GlassCard with title, 3-line text truncation, external link, "Открыть" button
- `VacancyModal` — Chakra `Modal` with full `job_text` and link button
- `ParseHistory` — collapsible list of past `parsing_jobs` with saved count badge

Design: Aurora glass aesthetic (consistent with existing UI — `GlassCard`, `GradientButton`, glass backdrop).

---

## 7. Concurrency Budget (16 GB RAM)

| Phase          | Workers | Semaphore | Est. RAM / worker |
|----------------|---------|-----------|-------------------|
| List pages     | 3       | 3         | ~80 MB            |
| Vacancy detail | 4       | 4         | ~80 MB            |
| Browser        | 1 shared| —         | ~150 MB base      |

Total peak: ~1 GB for scraper. Safe on 16 GB.

Max 5 search result pages → up to ~100 vacancy IDs → detail phase processes ~100 vacancies.

---

## 8. Implementation Order

1. **DB models + migrations** — `parsing_jobs`, `auto_parsed_jobs`
2. **Scraper service** — `hh_scraper.py` with phase 1 + phase 2 + SSE queue
3. **API router** — 5 endpoints, mount in `api.py`
4. **Frontend types + API client**
5. **`useAutoParse` hook** — SSE + localStorage restore
6. **`AutoParsePage` + sub-components**
7. **Sidebar link + i18n keys**
8. **End-to-end smoke test**

---

## 9. Open Questions / Decisions

- **Anti-bot protection:** Random delay 1–5s after each list page is implemented. May additionally need a realistic user-agent string if hh.ru blocks requests.
- **Duplicate handling:** If user runs same query twice, `INSERT OR IGNORE` on `vacancy_id + user_id` or just allow duplicates per `parsing_job_id`.
- **SSE auth:** Pass JWT as query param (`?token=...`) or use cookie. Current middleware reads from header — SSE `EventSource` can't set custom headers. Recommend query param or cookie.
- **Max pages env var:** `HH_MAX_PAGES=5` default, override via `.env`.
- **Area code:** hardcoded `area=1` (Moscow). Could be a user setting later.
