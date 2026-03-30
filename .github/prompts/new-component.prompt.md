---
description: "Scaffold a new React component in apps/client: component file, types, custom hook (if needed), and barrel export. Provide the component name and a brief description of what it renders or does."
argument-hint: "e.g. ChatMessage — renders a single chat bubble with role, content, and timestamp"
agent: "agent"
tools: [search, editFiles, problems]
---

Follow the [frontend instructions](../instructions/frontend.instructions.md) throughout.

## Task

Scaffold a complete React component for the following:

**$input** <!-- e.g. "CVCard — displays CV file info with delete button and upload date" -->

---

## Steps to complete

### 1. Determine the right location

- Feature-specific → `frontend/src/features/<feature>/components/<ComponentName>/`
- Shared page component → `frontend/src/pages/<ComponentName>.tsx`
- Shared hook → `frontend/src/hooks/use<Name>.ts`

### 2. Define props type (`<ComponentName>.tsx`)

- Declare a `<ComponentName>Props` interface at the top of the file.
- Import types from `@/types/` or `@/features/<feature>/types/`.
- No `any` — use explicit types or generics.

### 3. Write the component

- Named export only — no default exports.
- If the component needs data fetching, effects, or non-trivial state (>~20 lines of logic), extract that into `use<ComponentName>.ts` in the same folder.
- Use Chakra UI components and props for all styling — no raw CSS, no Tailwind.
- Every interactive element must have an accessible label.

```tsx
// ✅ correct shape
export function CVCard({ cv, onDelete }: CVCardProps) {
  return (
    <Card>
      <CardBody>
        <Text>{cv.filename}</Text>
        <Button onClick={() => onDelete(cv.id)} colorScheme="red" size="sm">
          Delete
        </Button>
      </CardBody>
    </Card>
  );
}
```

### 4. Custom hook (if needed) — `use<ComponentName>.ts`

- Return a typed object (not a positional array).
- Use `useQuery` / `useMutation` from React Query for API data.
- Keep hook in `hooks/` or feature `hooks/` folder.

### 5. Barrel export

- If inside a feature, add export to `features/<feature>/index.ts`.

### 6. Verify

- Run `get_errors` on all modified files and fix any TypeScript errors.

---

## Constraints

- No class components. No default exports for components.
- Import types from `@/types/` or `@/features/<feature>/types/`.
- All styling via Chakra UI props — no inline `style` props, no CSS classes.
- Environment variables accessed via `import.meta.env.VITE_*`.
- Use path aliases (`@/...`) — never deep relative paths.
- Forms must use React Hook Form + Zod validation.
