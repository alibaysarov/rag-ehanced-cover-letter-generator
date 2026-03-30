---
applyTo: "frontend/**"
description: "Use when: writing or modifying React/TypeScript frontend code — components, pages, hooks, API clients, forms, routing, or styling with Chakra UI."
---

# Frontend Instructions — React + TypeScript + Chakra UI

## Stack

- **Framework**: React 19 with TypeScript (strict mode)
- **Build**: Vite 7 (`npm run dev` on port 5173)
- **UI**: Chakra UI v2 (emotion-based) — no other CSS frameworks
- **State**: TanStack React Query v5 (no Redux/Zustand)
- **Routing**: React Router v7 with `BrowserRouter`
- **Forms**: React Hook Form v7 + Zod v4 validation + `@hookform/resolvers`
- **HTTP**: Axios (authenticated), fetch API (public)
- **Icons**: `@tabler/icons-react`, `react-icons`, `@chakra-ui/icons`
- **Package manager**: npm

## Project Structure

```
frontend/src/
├── api/client.ts                  # Query client + fetch utils + API_BASE_URL
├── features/
│   └── auth/
│       ├── api/auth-client.ts     # Axios instance + TokenManager + authService
│       ├── components/            # LoginPage, RegisterPage, Navigation, PrivateRoute
│       ├── hooks/useAuth.ts       # Auth state hook
│       ├── types/index.ts         # Auth interfaces
│       └── index.ts               # Barrel export
├── hooks/useLetter.ts             # Letter/CV mutations & queries
├── pages/                         # Top-level page components
│   ├── CVUploadPage.tsx
│   ├── LetterGenerator.tsx
│   └── UserCVPage.tsx
├── types/letter.ts                # Letter-related interfaces
├── App.tsx                        # Route definitions
├── main.tsx                       # Entry point with providers
└── style.css                      # Minimal global styles
```

## Import Rules

- Path aliases: `@/*` → `src/*` (configured in tsconfig + vite)
- Available aliases: `@/components/*`, `@/pages/*`, `@/hooks/*`, `@/types/*`, `@/api/*`
- Use barrel exports from `features/{feature}/index.ts`
- `import type` for TypeScript-only imports

## Component Conventions

- **Named exports only** — no default exports for components
- Component files: `.tsx`, pure logic files: `.ts`
- Props interface: `{ComponentName}Props`
- All UI via Chakra UI props — no raw CSS, no `style` props
- Extract hooks when component logic exceeds ~20 lines

```tsx
interface CVCardProps {
  cv: CV;
  onDelete: (id: number) => void;
}

export function CVCard({ cv, onDelete }: CVCardProps) {
  return (
    <Card>
      <CardBody>
        <Text>{cv.filename}</Text>
        <Button onClick={() => onDelete(cv.id)}>Delete</Button>
      </CardBody>
    </Card>
  );
}
```

## State Management (React Query)

- Query client configured with: `retry: 1`, `refetchOnWindowFocus: false`, `staleTime: 5 min`
- Use `useQuery` for reads, `useMutation` for writes
- Query keys: flat arrays in enum-like objects (e.g., `authKeys.user`, `cvOptions`)
- Invalidate related queries in `onSuccess` callbacks

```typescript
const { mutate, isPending } = useMutation({
  mutationFn: (data: FormData) => authApi.post('/letter/url', data),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['letters'] }),
});
```

## API Client Architecture

### Authenticated requests (Axios)

```typescript
// features/auth/api/auth-client.ts
export const authApi = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});
```

- Request interceptor injects `Authorization: Bearer {access_token}`
- Response interceptor handles 401 → auto-refresh token → retry original request
- On refresh failure: clear tokens, redirect to `/login`

### Public requests (fetch)

```typescript
// api/client.ts
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
```

## Authentication Flow

1. Login/Register → backend returns `{access_token, refresh_token}`
2. `TokenManager.setTokens()` stores in `localStorage`
3. `TokenManager.isTokenExpired()` checks JWT `exp` claim
4. `authService.isAuthenticated()` validates token existence + expiry
5. `PrivateRoute` guards protected routes (redirects to `/login`)
6. Axios interceptor handles automatic token refresh on 401

## Form Handling Pattern

```typescript
const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(6, 'Min 6 characters'),
});

type FormData = z.infer<typeof schema>;

const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
  resolver: zodResolver(schema),
});
```

- Zod schema defines validation rules
- `z.infer<typeof schema>` derives TypeScript type
- Display errors via `<FormErrorMessage>{errors.field?.message}</FormErrorMessage>`

## Routing

```
/login         → LoginPage (public)
/register      → RegisterPage (public)
/              → LetterGenerator (protected)
/upload-cv     → CVUploadPage (protected)
/my-cvs        → UserCVPage (protected)
*              → Redirect to /
```

Protected routes wrapped in `<PrivateRoute>`.

## Error Handling

- Form validation: Zod + `<FormErrorMessage>`
- API errors: `mutation.isError` → `mutation.error.message` in `<Alert status="error">`
- Auth errors: `useAuth` hook handles 401/403 → redirect to login
- Toast notifications: `useToast()` from Chakra for success/error feedback

## Provider Nesting Order (main.tsx)

```
StrictMode → QueryClientProvider → ChakraProvider → BrowserRouter → App → ReactQueryDevtools
```

## TypeScript Conventions

- Strict mode: `noUnusedLocals`, `noUnusedParameters`
- Interfaces for object contracts, types for unions/aliases
- Response types: `{Name}Response` with `success`, `data`, `message` pattern
- Never use `any` — use `unknown` + type guards
- Hooks return typed objects (not positional arrays)

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Components | PascalCase | `CVUploadPage`, `LoginPage` |
| Types | PascalCase + suffix | `LoginRequest`, `CVUploadResponse` |
| Hooks | camelCase + `use` prefix | `useAuth`, `useCVOptions` |
| Events | camelCase + `on` prefix | `onSubmit`, `onDelete` |
| Files | PascalCase for components | `LetterGenerator.tsx` |
| Type files | camelCase | `letter.ts`, `index.ts` |

## Environment Variables

Prefix with `VITE_` for frontend access:

- `VITE_API_URL` — backend API base URL (default: `http://localhost:8000/api/v1`)

## Critical Rules

1. **Chakra UI only** — no Tailwind, no raw CSS, no Material UI
2. **React Query for all server state** — no local state for API data
3. **Zod + React Hook Form** for all form validation
4. **Named exports** — never use default exports for components
5. **Path aliases** (`@/...`) — never relative paths with deep `../../`
6. **No `any`** — strict TypeScript throughout
