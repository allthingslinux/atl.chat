# Web (Next.js)

> Scope: Next.js web app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

Next.js web application for atl.chat. Loaded via root: `just web`.

## Tech Stack

Next.js 14 · React 18 · TypeScript · Tailwind CSS · shadcn/ui · Cloudflare Pages (next-on-pages)

## Repository Structure

```
app/
├── layout.tsx, page.tsx
└── globals.css

components/
└── ui/               # button, card, badge (shadcn)
lib/
└── utils.ts
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `just web dev` | Start Next.js dev server (port 3000) |
| `just web build` | Build for production |
| `just web start` | Start production server |
| `just web lint` | Ultracite check |
| `just web fix` | Ultracite fix |
| `just web type-check` | TypeScript check |

Env vars for dev: `NEXT_PUBLIC_IRC_WS_URL`, `NEXT_PUBLIC_XMPP_BOSH_URL` (set in justfile).

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [docs/services/web/](../../docs/services/web/)
