---
agent: agent
model: Claude Sonnet 4.5 (copilot)
description: "Convert OpenAI LLM calls from synchronous blocking to async streaming (SSE) across FastAPI and React"
---

# Spec: LLM Streaming Response

## 1. Overview

Currently `LetterService` calls `client.responses.create(...)` and `client.chat.completions.create(...)` using the synchronous `OpenAI` client. The full model response is buffered in memory before being returned to the user. For long cover letters (200–300 words) this means a perceivable wall of silence (typically 5–15 s) before any text appears.

This spec replaces that pattern with:
- **Backend**: `AsyncOpenAI` client + Server-Sent Events (SSE) streaming endpoints (`/letter/url/stream`, `/letter/text/stream`).
- **Frontend**: native `fetch()` streaming reader + a new `useStreamLetter` hook that progressively renders the letter token-by-token in `LetterGenerator`.

No database schema changes are required. Existing non-streaming endpoints (`/url`, `/text`) are kept intact as a fallback.

---

## 2. Architecture / Flow

```
Browser (LetterGenerator)
  │
  │  POST /api/v1/letter/url/stream   (multipart form, no response body)
  │  ← text/event-stream (SSE)
  ▼
FastAPI endpoint  (letter.py)
  │  StreamingResponse(generator, media_type="text/event-stream")
  ▼
LetterService.stream_by_url()  OR  stream_cover_letter()
  │  async generator → yields SSE lines
  ├──► _parse_job_requirements_from_url()   [AsyncOpenAI Responses API, stream=True]
  │       model: gpt-4.1-mini + web_search_preview tool
  │       yields each text-delta as it arrives
  └──► stream_cover_letter()               [AsyncOpenAI Responses API, stream=True]
          model: gpt-4o
          ┌──► embed query (sync, PdfService.embed_texts — stays sync for embeddings)
          ├──► Qdrant vector search  (stays sync via QdrantStorage.search)
          └──► AsyncOpenAI .responses.stream() → async for event → yield delta
```

SSE frame format:
```
data: {"delta": "<token>"}\n\n    ← incremental text
data: [DONE]\n\n                  ← end-of-stream sentinel
data: {"error": "<msg>"}\n\n      ← on exception
```

---

## 3. File Structure

```
backend/
  app/
    services/
      letter.py              ← UPDATED  (add AsyncOpenAI, add stream_* methods)
    api/
      v1/
        endpoints/
          letter.py          ← UPDATED  (add /url/stream and /text/stream routes)

frontend/
  src/
    hooks/
      useStreamLetter.ts     ← NEW      (streaming fetch hook)
      useLetter.ts           ← UPDATED  (re-export new hook from barrel)
    types/
      letter.ts              ← UPDATED  (add StreamLetterRequest, StreamChunk)
    pages/
      LetterGenerator.tsx    ← UPDATED  (consume useStreamLetter, render progressively)
    features/
      auth/
        api/
          auth-client.ts     ← READ ONLY (need getToken() helper — no changes expected)
```

---

## 4. Step-by-step Specification

### 4.1 Backend — `LetterService` (`backend/app/services/letter.py`)

**Import change** — add `AsyncOpenAI` alongside existing `OpenAI`:

```python
from openai import OpenAI, AsyncOpenAI
```

**Constructor change** — add `async_client`:

```python
class LetterService:
    def __init__(self, session: AsyncSession = None):
        self.client = OpenAI()          # kept for search_job_requirements
        self.async_client = AsyncOpenAI()  # ← NEW
        self.storage = QdrantStorage()
        self.session = session
        self.pdf_service = PdfService(session)
        self.cv_repository = CVRepository(session) if session else None
        self.letter_repository = LetterRepository(session) if session else None
```

**New method `stream_cover_letter`** — async generator replacing `generate_cover_letter`'s final OpenAI call:

```python
async def stream_cover_letter(
    self, job_requirements: str, source_id: int
) -> AsyncGenerator[str, None]:
    """
    Streams cover letter tokens as SSE-ready strings.
    Yields: raw text deltas (caller wraps in SSE frame).
    Raises: ValueError if no resume data found.
    """
    def _search_resume_data(query: str, top_k: int = 10) -> RAGSearchResult:
        query_vec = self.pdf_service.embed_texts([query])[0]
        found = self.storage.search(query_vector=query_vec, top_k=top_k)
        filtered_contexts, filtered_sources = [], []
        for context, source in zip(found["contexts"], found["sources"]):
            if str(source.get("source_id")) == str(source_id):
                filtered_contexts.append(context)
                filtered_sources.append(source)
        return RAGSearchResult(contexts=filtered_contexts, sources=filtered_sources)

    resume_data = _search_resume_data("ключевые навыки опыт образование достижения")
    if not resume_data.contexts:
        raise ValueError("Не найдены данные резюме в базе данных.")

    resume_context = "\n\n".join(f"- {c}" for c in resume_data.contexts)
    prompt = f"""...(same prompt as generate_cover_letter)..."""  # keep identical

    async with self.async_client.responses.stream(
        model="gpt-4o",
        input=prompt,
        max_output_tokens=2048,
        temperature=1.0,
    ) as stream:
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
```

**New method `stream_by_url`** — two-phase async generator:

```python
async def stream_by_url(
    self, job_url: str, source_id: int
) -> AsyncGenerator[str, None]:
    """
    Phase 1: stream job-requirement extraction.
    Phase 2: stream cover letter generation.
    Yields raw text deltas; caller wraps in SSE.
    """
    # Phase 1 — parse requirements (streaming, accumulate for phase 2)
    requirements_parts: list[str] = []
    async with self.async_client.responses.stream(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=f"... (same prompt as _parse_job_requirements_from_url) ...",
    ) as stream:
        async for event in stream:
            if event.type == "response.output_text.delta":
                requirements_parts.append(event.delta)
                # Do NOT yield phase-1 tokens to avoid mixing contexts;
                # they are only accumulated silently.

    job_requirements = "".join(requirements_parts)
    if not job_requirements:
        raise ValueError("Не удалось извлечь требования из URL.")

    # Phase 2 — stream letter
    async for delta in self.stream_cover_letter(job_requirements, source_id):
        yield delta
```

> **Note on phase-1 silence**: parsing the job page can take 3–10 s.
> To give the user progress feedback during phase 1, yield a special SSE frame type:
>
> ```python
> yield "__PARSING__"   # sentinel; frontend shows a "Analysing job post…" spinner
> ```
>
> Yield this once before `async with ... stream:` in phase 1, and yield `"__READY__"` after `job_requirements` is assembled but before phase 2 begins.

### 4.2 Backend — FastAPI Endpoints (`backend/app/api/v1/endpoints/letter.py`)

Add imports:

```python
import json
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
```

Add helper SSE wrapper (module-level private function):

```python
async def _sse_wrap(
    generator: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    try:
        async for delta in generator:
            if delta in ("__PARSING__", "__READY__"):
                yield f"data: {json.dumps({'status': delta})}\n\n"
            else:
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield "data: [DONE]\n\n"
    except ValueError as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    except Exception as exc:
        logger.exception("Streaming error")
        yield f"data: {json.dumps({'error': 'Internal streaming error'})}\n\n"
```

**New endpoint `/url/stream`**:

```python
@router.post("/url/stream")
async def stream_letter_from_url(
    url: str = Form(...),
    source_id: int = Form(...),
    letter_service: LetterService = Depends(get_letter_service),
):
    http_url = HttpUrl(url)   # validates; raises 422 automatically on bad input
    return StreamingResponse(
        _sse_wrap(letter_service.stream_by_url(str(http_url), source_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )
```

**New endpoint `/text/stream`**:

```python
@router.post("/text/stream")
async def stream_letter_from_text(
    name: str = Form(..., min_length=1, max_length=100),
    description: str = Form(..., min_length=1),
    source_id: int = Form(...),
    letter_service: LetterService = Depends(get_letter_service),
):
    job_requirements = f"{name}\n{description}"
    return StreamingResponse(
        _sse_wrap(letter_service.stream_cover_letter(job_requirements, source_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

> Both endpoints do **not** use `CurrentUser` — same pattern as existing `/url` and `/text` (auth is enforced by `AuthMiddleware` on the entire `/api/v1/letter` prefix).

### 4.3 Backend — No repository / schema / migration changes

No new DB tables or migrations are needed. The streaming endpoints do not persist the letter (same as existing endpoints). If letter persistence is added later, it should be a separate spec.

---

### 4.4 Frontend — Types (`frontend/src/types/letter.ts`)

Add to existing file:

```typescript
export interface StreamLetterRequest {
  source_id: number;
}
export interface StreamLetterFromUrlRequest extends StreamLetterRequest {
  url: string;
}
export interface StreamLetterFromTextRequest extends StreamLetterRequest {
  name: string;
  description: string;
}

export type StreamStatus = 'idle' | 'parsing' | 'streaming' | 'done' | 'error';

export interface StreamChunk {
  delta?: string;
  status?: '__PARSING__' | '__READY__';
  error?: string;
}
```

### 4.5 Frontend — `useStreamLetter` hook (`frontend/src/hooks/useStreamLetter.ts`)

New file. Uses native `fetch` (not axios) because axios does not expose the raw `ReadableStream` needed for SSE line-by-line reading without a library.

```typescript
import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth';
import type {
  StreamLetterFromUrlRequest,
  StreamLetterFromTextRequest,
  StreamStatus,
} from '@/types/letter';

interface UseStreamLetterReturn {
  content: string;
  status: StreamStatus;
  error: string | null;
  streamFromUrl: (req: StreamLetterFromUrlRequest) => void;
  streamFromText: (req: StreamLetterFromTextRequest) => void;
  reset: () => void;
}

export function useStreamLetter(): UseStreamLetterReturn {
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setContent('');
    setStatus('idle');
    setError(null);
  }, []);

  const _stream = useCallback(async (endpoint: string, body: FormData) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setContent('');
    setError(null);
    setStatus('parsing');

    const token = TokenManager.getToken();  // retrieve stored JWT

    try {
      const response = await fetch(`${API_BASE_URL}/letter/${endpoint}`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body,
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';  // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (raw === '[DONE]') {
            setStatus('done');
            return;
          }
          const chunk = JSON.parse(raw) as { delta?: string; status?: string; error?: string };
          if (chunk.error) {
            setError(chunk.error);
            setStatus('error');
            return;
          }
          if (chunk.status === '__PARSING__') {
            setStatus('parsing');
          } else if (chunk.status === '__READY__') {
            setStatus('streaming');
          } else if (chunk.delta) {
            setStatus('streaming');
            setContent(prev => prev + chunk.delta);
          }
        }
      }
      setStatus('done');
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return;
      setError((err as Error).message ?? 'Unknown error');
      setStatus('error');
    }
  }, []);

  const streamFromUrl = useCallback(
    (req: StreamLetterFromUrlRequest) => {
      const fd = new FormData();
      fd.append('url', req.url);
      fd.append('source_id', req.source_id.toString());
      _stream('url/stream', fd);
    },
    [_stream],
  );

  const streamFromText = useCallback(
    (req: StreamLetterFromTextRequest) => {
      const fd = new FormData();
      fd.append('name', req.name);
      fd.append('description', req.description);
      fd.append('source_id', req.source_id.toString());
      _stream('text/stream', fd);
    },
    [_stream],
  );

  return { content, status, error, streamFromUrl, streamFromText, reset };
}
```

> `TokenManager.getToken()` — verify this is the correct import path from `@/features/auth/api/auth-client.ts`. Adjust if the token retrieval helper has a different name.

### 4.6 Frontend — `useLetter.ts` barrel update

Re-export `useStreamLetter` from the hooks barrel (currently `useLetter.ts` does not re-export — add at bottom):

```typescript
export { useStreamLetter } from './useStreamLetter';
```

### 4.7 Frontend — `LetterGenerator.tsx` updates

Replace `useCreateLetterFromUrl` / `useCreateLetterFromText` streaming calls with `useStreamLetter`.

Key changes:

1. Import and instantiate `useStreamLetter`:
   ```typescript
   import { useStreamLetter } from '@/hooks/useLetter';
   const { content, status, error, streamFromUrl, streamFromText, reset } = useStreamLetter();
   ```

2. Replace `createFromUrl.mutate(...)` with `streamFromUrl(...)` in `handleUrlSubmit`.

3. Replace `createFromText.mutate(...)` with `streamFromText(...)` in `handleTextSubmit`.

4. Derive loading state: `const isLoading = status === 'parsing' || status === 'streaming';`

5. Replace result rendering logic:
   - Show `<Spinner />` + "Analysing job post…" text when `status === 'parsing'`
   - Show live `<Textarea value={content} isReadOnly />` growing token-by-token when `status === 'streaming'`
   - Show error `<Alert>` when `status === 'error'`
   - Copy-to-clipboard button enabled only when `status === 'done'`
   - "Generate" button disabled when `isLoading`

6. Add a "Stop" `<IconButton>` (visible during streaming) that calls `reset()`.

7. Remove local state variables `letterContentUrl` / `letterContentText` that previously held the full response — replace entirely with `content` from the hook.

---

## 5. Security Considerations

| Risk | Mitigation |
|---|---|
| JWT exposed in `fetch` headers | `TokenManager.getToken()` reads from `localStorage` — same security posture as existing Axios usage; no change in threat model |
| SSE endpoint accepts arbitrary `url` | `HttpUrl(url)` (Pydantic) validates scheme + format; only `http`/`https` accepted by default |
| Prompt injection via `url` / `description` fields | Fields are embedded in a controlled prompt template; `description` is truncated at `min_length=1` — add `max_length=2000` on the `/text/stream` endpoint consistent with existing `/text` endpoint (currently uses 1 for min, no reported max in streaming) |
| Streaming response leaks partial data on auth failure | Both new endpoints inherit session-level auth from `AuthMiddleware`, which rejects requests before the generator starts |
| Nginx / proxy response buffering causes delayed delivery | `X-Accel-Buffering: no` header disables Nginx buffering; Uvicorn streams natively |
| Aborted streams leaving OpenAI connections open | `AbortController` on the frontend triggers network cancellation; FastAPI `StreamingResponse` generator exits on client disconnect (ASGI cancel scope) |

---

## 6. Acceptance Criteria

- [ ] `AsyncOpenAI` client is instantiated once in `LetterService.__init__` (not per request)
- [ ] `stream_cover_letter(job_requirements, source_id)` is an `async def` generator using `AsyncOpenAI.responses.stream()`
- [ ] `stream_by_url(job_url, source_id)` silently accumulates phase-1 tokens and then yields phase-2 deltas
- [ ] `POST /api/v1/letter/url/stream` returns `Content-Type: text/event-stream` with SSE frames
- [ ] `POST /api/v1/letter/text/stream` returns `Content-Type: text/event-stream` with SSE frames
- [ ] SSE frame for successful delta: `data: {"delta": "<token>"}\n\n`
- [ ] SSE frame for end-of-stream: `data: [DONE]\n\n`
- [ ] SSE frame for error: `data: {"error": "<message>"}\n\n`
- [ ] `X-Accel-Buffering: no` header present on both streaming endpoints
- [ ] `useStreamLetter` hook exposes `content`, `status`, `error`, `streamFromUrl`, `streamFromText`, `reset`
- [ ] `status` transitions: `idle → parsing → streaming → done` (happy path); `idle → parsing → error` (failure)
- [ ] Frontend renders partial `content` progressively while `status === 'streaming'`
- [ ] "Stop" button visible and functional during streaming, calls `reset()` and aborts fetch
- [ ] Existing non-streaming endpoints `/url` and `/text` remain unmodified and functional
- [ ] No TypeScript `any` types introduced
- [ ] `TokenManager.getToken()` (or equivalent) correctly passes Bearer token in streaming fetch
- [ ] Backend does not crash on client disconnect mid-stream (generator exit is graceful)
- [ ] `description` field on `/text/stream` enforces `max_length=2000` to prevent oversized prompts
