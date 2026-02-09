# ToWow Website — Codex Instructions

## Stack
- Next.js 16 (App Router), React 19, TypeScript strict
- CSS Modules (*.module.css), NO Tailwind
- next-intl for i18n (zh + en)
- Deployed to Vercel

## Build & Test
```bash
npm run dev          # Dev server on port 3000
npm run build        # Production build (MUST pass before commit)
npm run lint         # ESLint check
```

## i18n Pattern
```tsx
import {useTranslations} from 'next-intl';
const t = useTranslations('namespace');
// Plain text: t('key')
// Rich text: t.rich('key', {bold: (c) => <b>{c}</b>})
// Messages: website/messages/zh/*.json + website/messages/en/*.json
```

## File Conventions
- Pages: `app/[locale]/(pages)/page-name/page.tsx`
- Components: `components/ComponentName.tsx` + `ComponentName.module.css`
- Shared styles: `styles/*.css`
- Static assets: `public/`

## Do NOT
- Use Tailwind or inline styles (project uses CSS Modules)
- Add new npm dependencies without explicit approval
- Modify `next.config.ts` or `middleware.ts` without approval
- Use `any` type — maintain strict TypeScript
- Import from `@/` alias — use relative paths or configured aliases only
