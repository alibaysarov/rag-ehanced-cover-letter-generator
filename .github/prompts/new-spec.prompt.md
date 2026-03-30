---
agent: agent
model: Claude Sonnet 4.6 (copilot)
description: "Template prompt for generating a new feature spec. Output is saved to .github/specs/active/."

---

You are a senior software architect. Your task is to generate a detailed implementation specification for the feature described below.

**Output rules:**
- Save the spec as a new file in `.github/specs/active/<feature-slug>.prompt.md`
- Use kebab-case for the filename derived from the feature name
- The output file must start with this exact frontmatter:
  ```
  ---
  agent: agent
  model: Claude Sonnet 4.5 (copilot)
  description: "<one-line description of the feature>"
  ---
  ```

**Spec must include the following sections:**

1. **Overview** — what the feature does and why
2. **Architecture / Flow** — ASCII diagram of the request/response flow across frontend ↔ backend ↔ PostgreSQL ↔ Qdrant ↔ OpenAI
3. **New file structure** — full list of files to create or modify with comments (← NEW / ← UPDATED)
4. **Step-by-step specification** — numbered sections, one per layer:
   - Pydantic schemas (`backend/app/schemas/`)
   - SQLModel definitions + Alembic migration (if DB is involved)
   - Repository implementation (`backend/app/repository/`)
   - Service implementation (`backend/app/services/`)
   - FastAPI endpoint + dependency injection (`backend/app/api/v1/endpoints/`)
   - React components + hooks (`frontend/src/`)
   - Any new lib wrappers
5. **Security considerations** — explicit list of risks and mitigations
6. **Acceptance Criteria** — checklist of `- [ ]` items that can be verified

**Constraints to follow (from project conventions):**
- Backend: Follow [backend instructions](../instructions/backend.instructions.md)
- Frontend: Follow [frontend instructions](../instructions/frontend.instructions.md)
- AI/LLM: Follow [AI integration instructions](../instructions/ai-integration.instructions.md)
- All imports as `from app.{module}` — never `from backend.app`
- Services must not create DB sessions — always receive via DI
- Repositories accept `AsyncSession` and use SQLAlchemy `select()`
- SQLModel with `table=True` for DB models, Pydantic `BaseModel` for schemas
- All endpoints must be `async def`
- Frontend uses Chakra UI, React Query, React Hook Form + Zod
- TypeScript `strict: true` — no `any`
- source_id must be consistent between PostgreSQL and Qdrant
- All feature files export from barrel `index.ts`

---

**Describe the feature you want a spec for:**

$input
