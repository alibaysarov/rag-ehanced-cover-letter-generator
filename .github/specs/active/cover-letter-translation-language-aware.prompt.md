---
agent: agent
model: Claude Sonnet 4.6 (copilot)
description: "Add cover letter translation button with language picker and enforce language-aware generation from the job prompt"
---

# Cover Letter Translation + Language-Aware Generation

## 1. Overview

Two connected sub-features:

**A. Translation button** — After a cover letter is generated and displayed, the user can select a target language from a dropdown and click "Translate". The backend streams the translated letter token-by-token via SSE, replacing the existing generated content in the same result card.

**B. Language-aware generation** — The generation prompts already contain a soft hint ("write in the language of the job posting"), but it is inconsistently applied. This spec formalises it: an optional `target_language` form field is added to both generation endpoints. When provided it is injected directly into the system prompt as a hard instruction; when absent the LLM auto-detects from the job text (existing behaviour, strengthened wording).

---

## 2. Architecture / Flow

### Translation flow
```
User selects language + clicks "Translate"
         │
         ▼
LetterGenerator.tsx
  useTranslateLetter() (streaming hook)
         │  POST /letter/translate/stream
         │  { text, target_language }
         ▼
letter.py endpoint (stream_translate_letter)
         │
         ▼
LetterService.stream_translate_letter(text, target_language)
         │  AsyncOpenAI chat.completions.stream
         │  model: gpt-4o
         ▼
SSE deltas → EventSource → UI updates translated content
```

### Language-aware generation flow
```
User submits form with optional language selector (generate form)
         │
         ▼
LetterGenerator.tsx adds `target_language` to FormData
         │  POST /letter/url/stream  or  /letter/text/stream
         │  { ..., target_language?: string }
         ▼
LetterService.stream_by_url / stream_cover_letter
  receives target_language param
  injects "Write the letter strictly in <LANG>." into system prompt
         │
         ▼
SSE deltas → existing useStreamLetter hook (no hook changes) → UI
```

---

## 3. New file structure

```
backend/app/schemas/letter.py          ← UPDATED  (TranslateLetterRequest)
backend/app/services/letter.py         ← UPDATED  (stream_translate_letter, target_language param)
backend/app/api/v1/endpoints/letter.py ← UPDATED  (POST /translate/stream, target_language Form field)

frontend/src/types/letter.ts           ← UPDATED  (TranslateRequest, LANGUAGES constant)
frontend/src/hooks/useLetter.ts        ← UPDATED  (useTranslateLetter hook, useStreamTranslate)
frontend/src/hooks/useStreamTranslate.ts  ← NEW   (streaming hook for translation)
frontend/src/pages/LetterGenerator.tsx ← UPDATED  (TranslatePanel component, language selector on generation form)
```

---

## 4. Step-by-step specification

### 4.1 Pydantic schemas — `backend/app/schemas/letter.py`

Add at the bottom of the file:

```python
class TranslateLetterRequest(BaseModel):
    """Request schema for translating an existing letter"""
    text: str = Field(..., min_length=1, description="Letter text to translate")
    target_language: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Target language name in English, e.g. 'Russian', 'German'",
    )
```

No DB changes required — translation is stateless (not persisted).

---

### 4.2 SQLModel / Alembic migration

**None required.** Translation is a stateless generation endpoint; no new columns or tables.

---

### 4.3 Service — `backend/app/services/letter.py`

#### 4.3.1 Add `stream_translate_letter`

Add a new async generator method to `LetterService`:

```python
async def stream_translate_letter(
    self, text: str, target_language: str
) -> AsyncGenerator[str, None]:
    """
    Translates an existing cover letter into target_language, streaming tokens.
    Raises ValueError for empty input.
    """
    if not text.strip():
        raise ValueError("Cannot translate empty text.")

    system_prompt = (
        "You are a professional translator specialising in business correspondence. "
        "Translate the provided cover letter into "
        f"{target_language}. "
        "Preserve all formatting, paragraph breaks, and professional tone. "
        "Output only the translated letter — no explanations or metadata."
    )

    async with self.async_client.chat.completions.stream(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        max_tokens=2048,
        temperature=0.3,
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
```

#### 4.3.2 Add `target_language` to `stream_cover_letter`

Modify the method signature and inject language instruction into the prompt:

```python
async def stream_cover_letter(
    self,
    job_requirements: str,
    source_id: int,
    target_language: str | None = None,   # ← ADD PARAM
) -> AsyncGenerator[str, None]:
    ...
    # Inside the prompt f-string, replace the language line:
    language_instruction = (
        f"Write the letter strictly in {target_language}."
        if target_language
        else "Write the letter in the same language as the job requirements."
    )

    prompt = f"""
You are a professional cover letter writing assistant.

Job requirements:
{job_requirements}

Candidate resume data:
{resume_context}

Task: Generate a personalised cover letter that:
- Shows how the candidate's experience maps to the role
- Uses keywords from the resume
- Matches specific resume achievements to job requirements (where technically relevant)
- Maintains a professional yet approachable tone
- Avoids clichés and generic phrases
- Is 200–300 words

{language_instruction}
"""
```

#### 4.3.3 Propagate `target_language` through `stream_by_url`

```python
async def stream_by_url(
    self,
    job_url: str,
    source_id: int,
    target_language: str | None = None,   # ← ADD PARAM
) -> AsyncGenerator[str, None]:
    ...
    # Pass it down:
    async for delta in self.stream_cover_letter(job_requirements, source_id, target_language):
        yield delta
```

Also add to `stream_by_text` (the text-based generation path) with identical signature change.

---

### 4.4 FastAPI endpoints — `backend/app/api/v1/endpoints/letter.py`

#### 4.4.1 New translation stream endpoint

```python
@router.post("/translate/stream")
async def stream_translate_letter(
    text: str = Form(..., description="Letter content to translate"),
    target_language: str = Form(..., description="Target language, e.g. 'Russian'"),
    letter_service: LetterService = Depends(get_letter_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    return StreamingResponse(
        _sse_wrap(letter_service.stream_translate_letter(text, target_language)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

#### 4.4.2 Update existing stream endpoints to accept `target_language`

In `stream_letter_from_url`:
```python
@router.post("/url/stream")
async def stream_letter_from_url(
    url: str = Form(...),
    source_id: int = Form(...),
    target_language: Optional[str] = Form(None),   # ← ADD
    letter_service: LetterService = Depends(get_letter_service),
):
    http_url = HttpUrl(url)
    return StreamingResponse(
        _sse_wrap(letter_service.stream_by_url(str(http_url), source_id, target_language)),
        ...
    )
```

In `stream_letter_from_text`:
```python
@router.post("/text/stream")
async def stream_letter_from_text(
    name: str = Form(...),
    description: str = Form(...),
    source_id: int = Form(...),
    target_language: Optional[str] = Form(None),   # ← ADD
    letter_service: LetterService = Depends(get_letter_service),
):
    ...
    # pass target_language to service
```

---

### 4.5 Frontend types — `frontend/src/types/letter.ts`

Add at the end of the file:

```typescript
/** ISO language name displayed to user and sent to API */
export interface Language {
  code: string;   // BCP-47 e.g. "ru", "en"
  label: string;  // Display name e.g. "Russian"
  apiName: string; // Name sent to LLM e.g. "Russian"
}

export const LANGUAGES: Language[] = [
  { code: 'en', label: 'English', apiName: 'English' },
  { code: 'ru', label: 'Русский', apiName: 'Russian' },
  { code: 'de', label: 'Deutsch', apiName: 'German' },
  { code: 'fr', label: 'Français', apiName: 'French' },
  { code: 'es', label: 'Español', apiName: 'Spanish' },
  { code: 'pt', label: 'Português', apiName: 'Portuguese' },
  { code: 'it', label: 'Italiano', apiName: 'Italian' },
  { code: 'pl', label: 'Polski', apiName: 'Polish' },
  { code: 'uk', label: 'Українська', apiName: 'Ukrainian' },
  { code: 'tr', label: 'Türkçe', apiName: 'Turkish' },
  { code: 'nl', label: 'Nederlands', apiName: 'Dutch' },
  { code: 'zh', label: '中文', apiName: 'Chinese (Simplified)' },
  { code: 'ar', label: 'العربية', apiName: 'Arabic' },
];

export interface TranslateRequest {
  text: string;
  target_language: string; // apiName from LANGUAGES
}
```

Also update `StreamLetterFromUrlRequest` and `StreamLetterFromTextRequest`:
```typescript
export interface StreamLetterFromUrlRequest extends StreamLetterRequest {
  url: string;
  target_language?: string;
}

export interface StreamLetterFromTextRequest extends StreamLetterRequest {
  name: string;
  description: string;
  target_language?: string;
}
```

---

### 4.6 New hook — `frontend/src/hooks/useStreamTranslate.ts`

Create a new file mirroring the pattern from `useStreamLetter.ts` but for translation:

```typescript
import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth/api/auth-client';
import type { TranslateRequest, StreamStatus } from '@/types/letter';

interface UseStreamTranslateReturn {
  content: string;
  status: StreamStatus;
  error: string | null;
  translate: (req: TranslateRequest) => void;
  reset: () => void;
}

export function useStreamTranslate(): UseStreamTranslateReturn {
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

  const translate = useCallback((req: TranslateRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setContent('');
    setError(null);
    setStatus('streaming');

    const formData = new FormData();
    formData.append('text', req.text);
    formData.append('target_language', req.target_language);

    const token = TokenManager.getToken();

    fetch(`${API_BASE_URL}/letter/translate/stream`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error('No response body');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const raw = line.slice(5).trim();
            if (raw === '[DONE]') {
              setStatus('done');
              return;
            }
            try {
              const parsed = JSON.parse(raw) as { delta?: string; error?: string };
              if (parsed.error) {
                setError(parsed.error);
                setStatus('error');
                return;
              }
              if (parsed.delta) {
                setContent((prev) => prev + parsed.delta);
              }
            } catch {
              // skip malformed lines
            }
          }
        }
        setStatus('done');
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
        setStatus('error');
      });
  }, []);

  return { content, status, error, translate, reset };
}
```

---

### 4.7 Update hook barrel — `frontend/src/hooks/useLetter.ts`

Add export at the bottom:

```typescript
export { useStreamTranslate } from './useStreamTranslate';
```

Also update `streamFromUrl` and `streamFromText` calls to forward optional `target_language` from the request object into the FormData:

```typescript
// In useStreamLetter (useStreamLetter.ts) streamFromUrl:
if (req.target_language) formData.append('target_language', req.target_language);

// Same for streamFromText
```

---

### 4.8 Frontend page — `frontend/src/pages/LetterGenerator.tsx`

#### 4.8.1 Language selector on generation forms

Add a `Select` for generation language directly above each submit button in both tabs:

```tsx
import { LANGUAGES } from '@/types/letter';

// State at top of component:
const [generateLanguage, setGenerateLanguage] = useState<string>('');

// JSX (add to both From URL and From Text tabs, above the submit Button):
<FormControl>
  <FormLabel>Letter language (optional)</FormLabel>
  <Select
    placeholder="Auto-detect from job posting"
    value={generateLanguage}
    onChange={(e) => setGenerateLanguage(e.target.value)}
  >
    {LANGUAGES.map((lang) => (
      <option key={lang.code} value={lang.apiName}>
        {lang.label}
      </option>
    ))}
  </Select>
  <FormHelperText>
    Leave blank to auto-detect from the job posting language
  </FormHelperText>
</FormControl>
```

Pass `target_language` in the submit handlers:

```typescript
const handleUrlSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  streamFromUrl({
    url,
    source_id: selectedSourceId,
    target_language: generateLanguage || undefined,
  });
};
```

#### 4.8.2 Translation panel

Inside the result `Card` (after the generated letter), add a translation section:

```tsx
import { useStreamTranslate } from '@/hooks/useLetter';

// New state:
const [translateLanguage, setTranslateLanguage] = useState<string>('');
const {
  content: translatedContent,
  status: translateStatus,
  error: translateError,
  translate,
  reset: resetTranslate,
} = useStreamTranslate();

const isTranslating = translateStatus === 'streaming';
const hasTranslation = (translateStatus === 'streaming' || translateStatus === 'done') && translatedContent;

// Add inside the result Card, after the generated letter Box:
<Divider my={4} />
<VStack spacing={3} align="stretch">
  <HStack>
    <Select
      placeholder="Translate to..."
      value={translateLanguage}
      onChange={(e) => setTranslateLanguage(e.target.value)}
      maxW="260px"
      isDisabled={streamStatus !== 'done' || isTranslating}
    >
      {LANGUAGES.map((lang) => (
        <option key={lang.code} value={lang.apiName}>
          {lang.label}
        </option>
      ))}
    </Select>
    <Button
      colorScheme="teal"
      isDisabled={!translateLanguage || streamStatus !== 'done' || isTranslating}
      isLoading={isTranslating}
      loadingText="Translating..."
      onClick={() => {
        resetTranslate();
        translate({ text: streamContent, target_language: translateLanguage });
      }}
    >
      Translate
    </Button>
    {hasTranslation && (
      <Button
        size="sm"
        variant="ghost"
        onClick={resetTranslate}
      >
        Clear
      </Button>
    )}
  </HStack>

  {translateError && (
    <Alert status="error">
      <AlertIcon />
      <AlertDescription>{translateError}</AlertDescription>
    </Alert>
  )}

  {hasTranslation && (
    <Box>
      <HStack justify="space-between" mb={2}>
        <Text fontWeight="semibold" fontSize="sm" color="gray.600">
          Translated letter
        </Text>
        <Button
          size="sm"
          colorScheme="blue"
          isDisabled={translateStatus !== 'done'}
          onClick={() => {
            navigator.clipboard.writeText(translatedContent);
            setShowCopiedAlert(true);
            setTimeout(() => setShowCopiedAlert(false), 2000);
          }}
        >
          Copy
        </Button>
      </HStack>
      <Box whiteSpace="pre-wrap" p={4} bg="teal.50" borderRadius="md" minH="100px">
        {translatedContent}
        {isTranslating && <Spinner size="xs" ml={1} />}
      </Box>
    </Box>
  )}
</VStack>
```

Import `Divider` from `@chakra-ui/react`.

---

## 5. Security considerations

| Risk | Mitigation |
|------|-----------|
| Unauthenticated access to `/translate/stream` | Endpoint uses `CurrentUser = Depends(get_current_user)` — 401 if token missing/invalid |
| Prompt injection via `text` field | The full letter text (generated by our own LLM) is passed as user turn content, not system prompt. Injection risk is low; add max length validation: `text: str = Form(..., max_length=10_000)` |
| Excessively large translation requests | Hard token cap `max_tokens=2048` in `stream_translate_letter`; `max_length=10_000` on Form field |
| Language field injection | `target_language` is interpolated into a system prompt string. Sanitise: strip newlines and limit to 50 chars (`max_length=50` on Form field and schema) |
| SSE flooding / resource exhaustion | Abort controller on frontend tears down fetch on component unmount; per-user rate limiting (existing middleware) applies |
| XSS from streamed content | Content is rendered inside `whiteSpace="pre-wrap"` Chakra `Box` (text node, not `dangerouslySetInnerHTML`) — safe |

---

## 6. Acceptance Criteria

### Backend
- [ ] `POST /letter/translate/stream` returns `200` with `text/event-stream` for valid authenticated request
- [ ] `POST /letter/translate/stream` returns `401` for unauthenticated request
- [ ] `POST /letter/translate/stream` sends `data: {"delta": "..."}` chunks and ends with `data: [DONE]`
- [ ] `POST /letter/translate/stream` sends `data: {"error": "..."}` for empty `text` field
- [ ] `POST /letter/url/stream` accepts optional `target_language` form field without breaking existing callers
- [ ] `POST /letter/text/stream` accepts optional `target_language` form field without breaking existing callers
- [ ] When `target_language` is provided, the generated letter is verifiably in that language
- [ ] When `target_language` is absent, the generated letter matches the language of the job text

### Frontend
- [ ] Language selector appears above the submit button in both "From URL" and "From Text" tabs
- [ ] Selecting no language sends no `target_language` field (auto-detect mode)
- [ ] After generation completes, the translate panel (language dropdown + "Translate" button) is visible
- [ ] "Translate" button is disabled while letter is still streaming or while translating
- [ ] Clicking "Translate" streams translated content into a separate `teal.50` card below the original
- [ ] "Copy" button under the translated card copies translated content (not original)
- [ ] "Clear" button removes the translated content
- [ ] The translate panel disappears / resets when a new generation is started (`resetStream` clears `streamContent`)
- [ ] `LANGUAGES` list renders all 13 languages correctly in both selectors
- [ ] `useStreamTranslate` abort controller fires on component unmount (no memory leak)
- [ ] TypeScript strict mode: no `any`, all types imported from `@/types/letter`
