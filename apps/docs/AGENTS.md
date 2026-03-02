# Docs (Fumadocs)

> Scope: Documentation site app. Inherits monorepo [AGENTS.md](../../AGENTS.md).

Fumadocs-powered documentation site for atl.chat. Next.js 16 + MDX content, deployed to Cloudflare Workers via OpenNext + Alchemy.

## Tech Stack

Next.js 16 · React 19 · Fumadocs (MDX) · Tailwind CSS 4 · Cloudflare Workers (OpenNext) · Alchemy (IaC deploy)

## Repository Structure

```
app/
├── layout.tsx, global.css
├── api/search/route.ts
├── llms.txt/route.ts, llms-full.txt/route.ts
├── llms.mdx/docs/[[...slug]]/route.ts
└── [[...slug]]/layout.tsx, page.tsx

components/
├── ai/page-actions.tsx
└── mdx/mermaid.tsx

content/docs/           # MDX documentation content
├── index.mdx
├── architecture/       # Data model, networking
├── development/        # Contributing, adding a service, testing
├── getting-started/    # Overview, local development
├── operations/         # Deployment, backups, monitoring, security, SSL, troubleshooting
├── reference/          # API, env vars, FAQ, glossary, ports
└── services/           # Per-service docs (atheme, bridge, irc, thelounge, web, webpanel, xmpp)

lib/                    # Utilities (cn, layout, source)
scripts/lint.ts         # Link validation script
source.config.ts        # Fumadocs source config
alchemy.run.ts          # Alchemy IaC deployment script
wrangler.jsonc          # Cloudflare Workers config
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `pnpm run dev` | Start dev server (port 3001) |
| `pnpm run build` | Build for production |
| `pnpm run deploy` | Build + deploy to Cloudflare Workers (staging) |
| `pnpm run deploy:prod` | Build + deploy to Cloudflare Workers (prod) |
| `pnpm run check-types` | Fumadocs MDX + Next.js typegen + tsc |
| `pnpm run lint:links` | Validate internal links |

## Related

- [Monorepo AGENTS.md](../../AGENTS.md)
- [docs-old/AGENTS.md](../../docs-old/AGENTS.md) — Legacy docs (pre-Fumadocs)
- [apps/web/AGENTS.md](../web/AGENTS.md)
