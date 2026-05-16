# Frontend Redesign — Aurora

## Context

The current frontend (React 19.2 + Chakra UI 2.10 + Framer Motion 12.38) is functional but architecturally and visually fragmented:

- **Navigation**: top-only header ([src/features/auth/components/Navigation.tsx:37-79](../frontend/src/features/auth/components/Navigation.tsx#L37-L79)) is duplicated inside individual pages (`ProjectsPage`, `CVUploadPage`) — no persistent layout shell.
- **No profile page**: only a logout item in the dropdown menu; user has nowhere to edit name/email or change password.
- **Cramped output**: [LetterGenerator.tsx:297](../frontend/src/pages/LetterGenerator.tsx#L297) hard-codes `minH="200px"` for the generated letter, which is half of what a typical 500–1000 word cover letter needs.
- **Abrupt routing**: routes swap with no transition; Framer Motion is already in dependencies but unused for page-level animation.
- **Generic visuals**: default Chakra `blue`/`green`/`teal` `colorScheme` across the app, no typographic identity, `gray.50` page background.

Per the user's references (shift.careers, aiapply.co), the redesign reorganizes the shell around a persistent left sidebar, adds a Profile page, introduces smooth fade+slide page transitions, expands and rebuilds the letter generator, and commits the app to a unified **Aurora** aesthetic — soft indigo→fuchsia→cyan gradient mesh background with glassmorphic cards, vibrant gradient accents, generous rounded geometry.

---

## Design System: Aurora

A modern AI-product aesthetic: a low-saturation aurora gradient mesh as the page surface, glassmorphic frosted cards floating on top, vivid gradient CTAs. Feels alive and forward-looking without being noisy.

### Background (page-level)

A fixed full-viewport gradient mesh in `AppShell`, rendered as three overlapping radial gradients:

```css
background:
  radial-gradient(at 18% 12%, rgba(99, 102, 241, 0.22) 0px, transparent 50%),   /* indigo top-left */
  radial-gradient(at 82% 28%, rgba(217, 70, 239, 0.18) 0px, transparent 55%),   /* fuchsia top-right */
  radial-gradient(at 50% 92%, rgba(6, 182, 212, 0.20) 0px, transparent 55%),    /* cyan bottom */
  #FAFAFB;
```

Optional very faint noise overlay (0.02 opacity, CSS data-uri) to kill banding. The mesh is **static** — it does not animate (to avoid distraction during long writing sessions).

### Glass surfaces (cards, sidebar, modals)

```css
background: rgba(255, 255, 255, 0.55);
backdrop-filter: blur(24px) saturate(160%);
-webkit-backdrop-filter: blur(24px) saturate(160%);
border: 1px solid rgba(255, 255, 255, 0.6);
border-radius: 24px;          /* rounded-3xl */
box-shadow:
  0 1px 0 rgba(255, 255, 255, 0.6) inset,           /* top highlight */
  0 8px 32px rgba(79, 70, 229, 0.08),               /* indigo glow */
  0 2px 8px rgba(15, 23, 42, 0.04);                 /* depth */
```

Fallback (no `backdrop-filter` support, e.g. older Firefox): solid `rgba(255,255,255,0.85)` via `@supports not (backdrop-filter: blur(1px))`.

### Color tokens (`src/theme/colors.ts`)

| Token | Hex / value | Use |
|---|---|---|
| `aurora.indigo` | `#6366F1` | Gradient stop, primary brand |
| `aurora.fuchsia` | `#D946EF` | Gradient stop, accent |
| `aurora.cyan` | `#06B6D4` | Gradient stop, success/info |
| `slate.900` | `#0F172A` | Primary text |
| `slate.700` | `#334155` | Secondary text |
| `slate.500` | `#64748B` | Tertiary, placeholders |
| `slate.200` | `#E2E8F0` | Divider, subtle border |
| `surface.glass` | `rgba(255,255,255,0.55)` | Card bg |
| `surface.glassStrong` | `rgba(255,255,255,0.72)` | Hover / raised glass |
| `accent.gradient` | `linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)` | CTAs, active nav indicator |
| `danger.500` | `#E11D48` | Destructive |
| `success.500` | `#10B981` | Success states |

The gradient is the brand — used for primary CTAs, active sidebar item indicator, focus ring, logo mark.

### Typography (`src/theme/fonts.ts`)

- **Display**: `Bricolage Grotesque Variable` — modern, slightly characterful (opsz + wdth + wght axes), distinctive without being decorative.
- **Body**: `DM Sans Variable` — clean refined sans, NOT Inter / Roboto / Space Grotesk.
- **Mono**: `JetBrains Mono` — for URLs, code, metadata pills.

Loaded via `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/dm-sans`, `@fontsource/jetbrains-mono` and imported once in [src/main.tsx](../frontend/src/main.tsx).

### Motion

- **Page transitions**: opacity 0→1 (240ms) + y `12px→0` enter / `0→-8px` exit (320ms), ease `[0.4, 0, 0.2, 1]`.
- **Sidebar items**: 180ms background fade on hover; active state slides a thin gradient bar in from left (`scaleY 0→1`, 220ms).
- **Glass cards on hover**: subtle lift (`y: -2px`, shadow intensity bump, 200ms) — only on interactive cards.
- **Buttons (gradient CTA)**: gradient shifts on hover via `background-position` transition (400ms) to give a "shimmer".
- **Streaming letter**: blinking caret + soft fade-in for newly arrived chunks via Framer Motion `layout`.

---

## Architecture

```
src/
├── theme/                      [NEW]
│   ├── index.ts                — extendTheme entry
│   ├── colors.ts               — Aurora palette tokens
│   ├── fonts.ts                — font stacks (Bricolage / DM Sans / JBM)
│   └── components.ts           — Button/Input/Card variants (glass + gradient)
├── layouts/                    [NEW]
│   ├── AppShell.tsx            — sidebar + content + gradient mesh bg
│   ├── Sidebar.tsx             — glass sidebar
│   └── PageTransition.tsx      — AnimatePresence wrapper
├── components/
│   ├── ui/                     [NEW]
│   │   ├── SidebarItem.tsx     — nav item with gradient active bar
│   │   ├── UserCard.tsx        — glass user widget
│   │   ├── GlassCard.tsx       — reusable glass surface
│   │   └── GradientButton.tsx  — gradient CTA primitive
│   └── letter/                 [NEW]
│       ├── LetterForm.tsx
│       └── LetterOutput.tsx
├── pages/
│   ├── ProfilePage.tsx         [NEW]
│   └── (existing pages refactored)
└── features/auth/
    ├── api/auth-client.ts      [MODIFY] add updateProfile, changePassword
    └── hooks/useAuth.ts        [MODIFY] expose new mutations
```

---

## Component Specs

### 1. AppShell — `src/layouts/AppShell.tsx`

Wraps all authenticated routes. Three layers:

1. **Background layer** (fixed, full viewport): the gradient mesh + optional noise.
2. **Sidebar** (260px fixed on `≥ md`, Drawer on `< md`): glass.
3. **Main** (`flex: 1`, scrollable): `Container maxW="1120px"`, padding `px={{ base: 6, md: 12 }} py={10}`, `PageTransition` wraps `children`.

```tsx
<Box position="relative" minH="100vh">
  <AuroraBackground />          {/* fixed, z=-1, pointer-events: none */}
  <Flex minH="100vh">
    <Sidebar />
    <Box as="main" flex="1" overflowY="auto">
      <Container maxW="1120px" px={{ base: 6, md: 12 }} py={10}>
        <PageTransition>{children}</PageTransition>
      </Container>
    </Box>
  </Flex>
</Box>
```

### 2. Sidebar — `src/layouts/Sidebar.tsx`

Glass surface, 260px wide, full viewport height, `position: sticky; top: 0`.

- **Top (brand)** `px={6} py={6}`: gradient logo mark (24×24 rounded square filled with `accent.gradient`) + wordmark "Coverly" in Bricolage Grotesque 600.
- **Middle (nav)** `px={3}`: `SidebarItem` entries — Generate (`IconSparkles`), Projects (`IconBriefcase`), Resumes (`IconFile`), Profile (`IconUserCircle`).
- **Bottom (user)** `px={3} py={5}`, hairline divider `slate.200/40`: `UserCard` (avatar gradient circle with initials, name + email truncated, logout icon-button).

Mobile: replace with `Chakra Drawer` triggered by a glass hamburger button fixed at top-left of main content.

### 3. SidebarItem — `src/components/ui/SidebarItem.tsx`

Built on `NavLink` (react-router-dom v7).

- Default: padding `px={3} py={2.5}`, text `slate.700`, transparent bg, `borderRadius="xl"`.
- Hover: bg `surface.glassStrong`, transition 180ms.
- Active: bg `surface.glassStrong`, text `slate.900`, **3px gradient bar slides in from left** (`accent.gradient`, scaleY 0→1, 220ms via Framer Motion); icon tints to indigo.

### 4. GlassCard — `src/components/ui/GlassCard.tsx`

Reusable wrapper using the glass token set above. Props: `padding`, `hover?: boolean` (enables lift on hover), `radius?: '2xl' | '3xl'`.

### 5. GradientButton — `src/components/ui/GradientButton.tsx`

Primary CTA. Variants:
- `solid` (default): background `accent.gradient`, white text, shadow `0 4px 16px rgba(99,102,241,0.35)`, hover background-position animates for shimmer.
- `outline`: 1.5px gradient border via `background-clip: padding-box, border-box`, gradient text.
- `ghost`: transparent, gradient text on hover.

Uses Chakra's `forwardRef` so it's a drop-in for `<Button>`.

### 6. PageTransition — `src/layouts/PageTransition.tsx`

Keyed on `useLocation().pathname`. `AnimatePresence mode="wait"` + `motion.div` with enter/exit per "Motion" above.

### 7. ProfilePage — `src/pages/ProfilePage.tsx`

Three stacked `GlassCard` sections:

1. **Personal Information** — `first_name`, `last_name`, `email`. React Hook Form + Zod (same pattern as [LoginPage.tsx](../frontend/src/features/auth/components/LoginPage.tsx)). "Save changes" → `updateProfile` mutation, `GradientButton`.
2. **Password** — `current_password`, `new_password`, `confirm_password`. Zod `min(8)` + match `refine`. "Update password" → `changePassword`.
3. **Preferences** — UI language toggle (RU/EN) + default generation language `Select` (from `LANGUAGES` in [src/types/letter.ts](../frontend/src/types/letter.ts)). Persist to `localStorage`; LetterForm reads on mount.

Toasts via `useToast` on success/error.

> **Backend dependency**: `PUT /auth/me` and `POST /auth/change-password`. Verify presence in [backend/app/api/auth.py](../backend/app/api/auth.py) before wiring; if missing, flag for backend implementer. Frontend can still ship preferences (client-side only).

### 8. LetterGenerator redesign — `src/pages/LetterGenerator.tsx`

Two-pane grid: **Form (left, 1fr)** + **Output (right, 1.5fr)** on `≥ lg`. Stacks below `lg`.

**Left — `LetterForm.tsx`** (one `GlassCard`):
- Segmented control "From URL / From Text" at top (replaces Chakra Tabs — cleaner pill toggle with gradient indicator on active segment).
- URL mode: `Input type="url"` + language `Select`.
- Text mode: name `Input` + description `Textarea` (rows={10}, allow vertical resize — currently locked at [LetterGenerator.tsx:199](../frontend/src/pages/LetterGenerator.tsx#L199)) + language `Select`.
- Full-width `GradientButton` "Generate" at bottom.

**Right — `LetterOutput.tsx`** (one taller `GlassCard`):
- **Idle**: glass card with a soft gradient orb illustration + "Your generated letter will appear here."
- **Parsing**: 6–8 shimmer skeleton lines (animated gradient sweep).
- **Streaming / done**:
  - Output box `minH="640px"` (was 200px), inner bg `rgba(255,255,255,0.6)`, padding `p={10}`, max-width prose width, `line-height={1.75}`, `font="body"` (DM Sans).
  - **Floating glass toolbar** above output: Copy (`GhostButton`), Stop (only while streaming, danger tint), Translate dropdown inline, word-count + estimated read-time pill (mono font).
  - **Translation as sibling tab** (Original / Translated) — not stacked below. Same styling.

Hooks unchanged: `useStreamLetter`, `useStreamTranslate` ([src/hooks/](../frontend/src/hooks/)). Remove dead `createFromUrl`/`createFromText` imports + `void` statements at [LetterGenerator.tsx:51-52, 72-73](../frontend/src/pages/LetterGenerator.tsx#L51-L73).

### 9. Theme entry — `src/theme/index.ts`

```ts
import { extendTheme } from '@chakra-ui/react';
import { colors } from './colors';
import { fonts } from './fonts';
import { components } from './components';

export const theme = extendTheme({
  config: { initialColorMode: 'light', useSystemColorMode: false },
  colors,
  fonts,
  styles: {
    global: {
      'html, body': { bg: 'transparent', color: 'slate.900' },
      'body': { fontFamily: 'body' },
      'h1, h2, h3, h4': { fontFamily: 'heading', letterSpacing: '-0.02em' },
      '*:focus-visible': {
        outline: 'none',
        boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.35)',
        borderRadius: '8px',
      },
    },
  },
  components,
});
```

`components.ts` overrides:
- **Button**: variants `solid` (uses `GradientButton` gradient), `glass` (`surface.glass` bg, slate text), `ghost` (transparent, hover `surface.glassStrong`), `link` (gradient text on hover).
- **Input / Textarea / Select**: bg `rgba(255,255,255,0.6)`, border `slate.200/60`, focus border indigo with soft gradient glow shadow.
- **Card**: glass token set, radius `3xl`.
- **Modal/Drawer**: glass surface for backdrop content; the overlay itself: `bg="blackAlpha.300"` + `backdrop-filter: blur(8px)`.

---

## Files to Create

| Path | Purpose |
|---|---|
| `frontend/src/theme/index.ts` | Theme entry |
| `frontend/src/theme/colors.ts` | Aurora palette tokens |
| `frontend/src/theme/fonts.ts` | Bricolage + DM Sans + JBM stacks |
| `frontend/src/theme/components.ts` | Glass / gradient component variants |
| `frontend/src/layouts/AppShell.tsx` | Sidebar + content + AuroraBackground |
| `frontend/src/layouts/Sidebar.tsx` | Glass left nav |
| `frontend/src/layouts/PageTransition.tsx` | Framer Motion wrapper |
| `frontend/src/components/ui/AuroraBackground.tsx` | Fixed gradient mesh layer |
| `frontend/src/components/ui/GlassCard.tsx` | Reusable glass surface |
| `frontend/src/components/ui/GradientButton.tsx` | Gradient CTA primitive |
| `frontend/src/components/ui/SidebarItem.tsx` | Nav item with gradient active bar |
| `frontend/src/components/ui/UserCard.tsx` | Sidebar user widget |
| `frontend/src/components/letter/LetterForm.tsx` | Form pane (extracted) |
| `frontend/src/components/letter/LetterOutput.tsx` | Output pane (extracted) |
| `frontend/src/pages/ProfilePage.tsx` | New profile page |

## Files to Modify

| File | Change |
|---|---|
| [frontend/src/main.tsx](../frontend/src/main.tsx) | Replace inline theme with `import { theme } from './theme'`; import fontsource fonts |
| [frontend/src/App.tsx](../frontend/src/App.tsx) | Wrap protected routes in `AppShell`; drop `Navigation` import; add `/profile` route under `PrivateRoute`; fix missing `PrivateRoute` on `/my-cvs` ([App.tsx:41-45](../frontend/src/App.tsx#L41-L45)); remove duplicate redundant root route ([App.tsx:69](../frontend/src/App.tsx#L69)); drop unused `sourceId` state ([App.tsx:18-26](../frontend/src/App.tsx#L18-L26)) |
| [frontend/src/pages/LetterGenerator.tsx](../frontend/src/pages/LetterGenerator.tsx) | Full visual rewrite per Spec §8; split into LetterForm + LetterOutput; remove embedded nav buttons; clean unused imports |
| [frontend/src/pages/UserCVPage.tsx](../frontend/src/pages/UserCVPage.tsx) | Remove embedded `Navigation`; restyle table using `GlassCard`; gradient CTAs |
| [frontend/src/pages/ProjectsPage.tsx](../frontend/src/pages/ProjectsPage.tsx) | Remove embedded `Navigation`; project cards become `GlassCard` with hover lift; badges in gradient/glass styling |
| [frontend/src/pages/CVUploadPage.tsx](../frontend/src/pages/CVUploadPage.tsx) | Remove embedded `Navigation`; restyle drop-zone as glass with gradient dashed border on drag-over |
| [frontend/src/features/auth/components/LoginPage.tsx](../frontend/src/features/auth/components/LoginPage.tsx) | Restyle to Aurora: glass card on gradient mesh bg, Bricolage heading, `GradientButton` (public route, no sidebar) |
| [frontend/src/features/auth/components/RegisterPage.tsx](../frontend/src/features/auth/components/RegisterPage.tsx) | Same as Login |
| [frontend/src/features/auth/components/Navigation.tsx](../frontend/src/features/auth/components/Navigation.tsx) | **DELETE** — replaced by `Sidebar` |
| [frontend/src/features/auth/api/auth-client.ts](../frontend/src/features/auth/api/auth-client.ts) | Add `authService.updateProfile(data)`, `authService.changePassword(data)` |
| [frontend/src/features/auth/hooks/useAuth.ts](../frontend/src/features/auth/hooks/useAuth.ts) | Expose `updateProfile`, `changePassword` mutations |
| [frontend/package.json](../frontend/package.json) | Add `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/dm-sans`, `@fontsource/jetbrains-mono` |

## Reusable Existing Code

- `useAuth` hook — sidebar user widget, profile forms.
- `useStreamLetter`, `useStreamTranslate` — keep unchanged; only LetterGenerator UI changes.
- `LANGUAGES` ([src/types/letter.ts](../frontend/src/types/letter.ts)) — feeds language selects everywhere.
- React Hook Form + Zod pattern from `LoginPage` — reuse for ProfilePage forms.
- `authApi` axios instance + interceptor stack — extend, don't rebuild.
- `useToast` pattern — keep across all save/error flows.
- `framer-motion` `AnimatePresence` — already used in `ProjectsPage` for card animations; same primitive at route level.

---

## Verification

1. **Install fonts**:
   ```bash
   cd frontend && npm install @fontsource-variable/bricolage-grotesque @fontsource-variable/dm-sans @fontsource/jetbrains-mono
   ```
2. **Start dev server**: `npm run dev` from `frontend/` → open `http://localhost:5173`.
3. **Gradient mesh + glass**:
   - Background shows soft indigo→fuchsia→cyan gradient mesh — no banding, no flicker.
   - Cards have visible backdrop-blur on top of the gradient (verify in Chrome and Firefox).
   - Fallback solid bg renders in older Firefox (toggle `backdrop-filter` off via DevTools).
4. **Sidebar / navigation**:
   - Glass sidebar visible on left across `/`, `/projects`, `/my-cvs`, `/profile`, `/upload-cv`.
   - Active nav item shows gradient left-bar + slight glass lift.
   - Logout from user card works (redirects `/login`).
   - Resize to < 768px: sidebar collapses into Drawer, hamburger toggle works.
5. **Page transitions**: clicking between nav items shows fade + slight Y-slide (not abrupt). Forward and back both animate.
6. **Profile page** (`/profile`):
   - Form prefills with current user (`first_name`, `last_name`, `email`).
   - "Save changes" calls `PUT /auth/me` → toast on success → `useAuth` refetches.
   - Password form rejects mismatch / `< 8` chars; on success → toast.
   - Preferences (UI lang + default gen language) persist across refresh (localStorage).
7. **LetterGenerator**:
   - Output area is visibly ~640px tall on desktop, glass card.
   - Floating glass toolbar (Copy, Stop, Translate, word count) above output.
   - Form mode toggle URL/Text swaps form smoothly with segmented gradient indicator.
   - Streaming letter shows blinking caret while `status === 'streaming'`.
   - Translation switches via Original/Translated tab — not stacked below.
8. **Theme**:
   - All primary CTAs use the indigo→fuchsia gradient; no leftover Chakra blue/green/teal.
   - Focus rings are indigo glow.
   - Bricolage Grotesque visible in headings, DM Sans in body, JBM in URLs / word-count pill.
9. **Type check**: `npm run build` (or `npx tsc --noEmit`) passes without errors.
10. **Login / Register** still work end-to-end and pick up the new palette + glass forms.

## Out of Scope

- Backend additions (`PUT /auth/me`, `POST /auth/change-password`) — flag for backend implementer if not present in [backend/app/api/auth.py](../backend/app/api/auth.py).
- Dark mode toggle — light Aurora only for V1.
- Full i18n implementation — only preference storage for V1.
- Animated gradient mesh — static for performance and focus.
- Markdown rendering of generated letters (current plain-text behavior preserved).
