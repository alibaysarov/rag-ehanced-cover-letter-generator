---
applyTo: "backend/app/services/{letter,pdf}.py,backend/app/storage/**,backend/app/schemas/rag.py"
description: "Use when: working with OpenAI API calls, embeddings, RAG pipeline, Qdrant vector search, PDF processing, prompt engineering, or LLM-based generation in Python."
---

# AI Integration Instructions — OpenAI + RAG + Qdrant

## Architecture Overview

RAG pipeline: PDF → chunks → embeddings → Qdrant → vector search → context assembly → GPT generation.

Dual-database pattern:
- **PostgreSQL**: metadata (users, CVs, letters) via SQLModel
- **Qdrant**: resume vectors for semantic search (cosine similarity)
- **`source_id`**: links records across both systems — always filter by it

## OpenAI Client

```python
from openai import OpenAI
client = OpenAI()  # Uses OPENAI_API_KEY from environment
```

- Client instantiated in `PdfService` (embeddings) and `LetterService` (generation)
- API key loaded from `OPENAI_API_KEY` env var (required)
- All calls are synchronous (OpenAI Python SDK)

## Embedding Model

| Parameter | Value |
|-----------|-------|
| Model | `text-embedding-3-large` |
| Dimensions | `3072` |
| API method | `client.embeddings.create()` |

```python
response = client.embeddings.create(
    model="text-embedding-3-large",
    dimensions=3072,
    input=texts,  # List[str] — batch for efficiency
)
embeddings = [item.embedding for item in response.data]
```

**Critical**: Vector dimensions (3072) must match Qdrant collection config. Changing requires re-embedding all data.

## PDF Processing Pipeline

1. **Load PDF**: `llama_index.readers.file.PDFReader`
2. **Chunk**: `SentenceSplitter(chunk_size=1000, chunk_overlap=0)` — sentence-aware splitting
3. **Embed**: batch embed all chunks via `embed_texts()`
4. **Generate IDs**: `abs(hash(f"{filename}_{source_id}_{chunk_index}"))` — deterministic
5. **Upsert to Qdrant**: points with payloads containing text + metadata
6. **Save metadata to PostgreSQL**: filename, file_size, source_id

### Qdrant Payload Structure

```python
{
    "user_id": int,        # User who uploaded
    "text": str,           # Chunk content
    "source": str,         # PDF file path
    "source_id": str|int,  # CV identifier (links to PostgreSQL)
    "chunk_index": int,    # Position in document
}
```

## Qdrant Configuration

| Setting | Value |
|---------|-------|
| Collection name | `"cvs"` |
| Vector size | `3072` |
| Distance metric | `COSINE` |
| URL | `http://localhost:6333` (configurable via `QDRANT_URL`) |
| Port | `6333` |

```python
client.create_collection(
    collection_name="cvs",
    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
)
```

## RAG Search Pattern

```python
# 1. Embed the query
query_vec = pdf_service.embed_texts([query])[0]

# 2. Search Qdrant
found = storage.search(query_vector=query_vec, top_k=10)

# 3. CRITICAL: Filter by source_id (multi-user safety)
filtered_contexts = [
    c for c, s in zip(found["contexts"], found["sources"])
    if str(s.get("source_id")) == str(source_id)
]

# 4. Assemble context
resume_context = "\n\n".join(f"- {c}" for c in filtered_contexts)
```

**Never skip source_id filtering** — it prevents cross-user data leakage.

## LLM Generation

### Chat Completions API

Use `client.chat.completions.create()` for text generation:

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.7,
    max_tokens=2048,
)
result = response.choices[0].message.content
```

### Responses API (with tools)

Use `client.responses.create()` for tool-augmented calls (e.g., web search):

```python
response = client.responses.create(
    model="gpt-4o-mini",
    tools=[{"type": "web_search_preview"}],
    input=prompt,
)
result = response.output_text
```

### Model Selection Guidelines

| Task | Recommended Model | Temperature | Max Tokens |
|------|------------------|-------------|------------|
| Cover letter generation | `gpt-4o` | 0.7–1.0 | 2048 |
| Job requirements extraction | `gpt-4o-mini` | 0.7 | 800 |
| URL/page parsing | `gpt-4o-mini` | 0.5 | 1500 |
| Simple classification | `gpt-4o-mini` | 0.3 | 200 |

## Prompt Construction

Prompts are in Russian (project language). Key patterns:

### System prompt for letter generation

```python
prompt = f"""
    Ты - помощник по созданию профессиональных сопроводительных писем.
    
    У тебя есть:
    1. Требования к вакансии: {job_requirements}
    2. Данные из резюме кандидата: {resume_context}
    
    Задача: сгенерировать персонализированное письмо (200-300 слов), которое:
    - Показывает почему мой опыт поможет в их работе
    - Имеет ключевые слова из резюме
    - Сопоставляет кейсы из релевантного опыта к требованиям вакансии
    - Пишется в профессиональном, но дружелюбном тоне
    - Избегает общих фраз
    - На языке требований для вакансии
"""
```

### Prompt guidelines

- Always inject retrieved resume context from Qdrant
- Include job requirements/description in the prompt
- Specify output language to match job posting language
- Keep prompts focused — one task per API call
- Include word count constraints (200-300 words for letters)

## Error Handling

```python
try:
    response = client.chat.completions.create(...)
    return response.choices[0].message.content
except Exception as e:
    logging.error(f"OpenAI API error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail="Generation failed")
```

- Wrap all OpenAI/Qdrant calls in try/except
- Log errors with `exc_info=True` for stack traces
- Return user-friendly error messages
- On CV deletion failure: backup Qdrant points → delete → restore on error

## Qdrant Operations Reference

| Operation | Method | Use Case |
|-----------|--------|----------|
| Search | `client.query_points()` | RAG retrieval |
| Upsert | `client.upsert()` | Upload CV chunks |
| Delete by filter | `client.delete()` with `Filter` + `FieldCondition` | Remove CV vectors |
| Get by source_id | `client.scroll()` with filter | Backup before deletion |

### Delete pattern

```python
client.delete(
    collection_name="cvs",
    points_selector=Filter(
        must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]
    ),
)
```

## Critical Rules

1. **Always filter Qdrant results by `source_id`** — prevents cross-user data leakage
2. **Vector size = 3072** — must match `text-embedding-3-large` output
3. **Batch embeddings** — pass list of texts to `embed_texts()`, not one at a time
4. **Deterministic point IDs** — use `abs(hash(...))` for reproducible upserts
5. **Never expose OpenAI API key** in responses, logs, or error messages
6. **OpenAI client uses env var** — never hardcode API keys
7. **Chunk size = 1000, overlap = 0** — changing requires re-processing all CVs
8. **String comparison for source_id** — always `str(source_id)` when filtering
