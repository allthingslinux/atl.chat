# atl.chat Monorepo

Welcome to the `atl.chat` ecosystem! This monorepo houses the full stack for the **allthingslinux** chat platform, integrating modern web technologies with established chat protocols like XMPP and IRC.

## 🚀 Repository Structure

The project is managed as a **pnpm workspace** using **Turborepo** for orchestration.

| Path | Application | Description | Tech Stack |
|------|-------------|-------------|------------|
| **[`apps/web`](./apps/web)** | **Landing Page** | The main landing page for `atl.chat`. | Next.js 14, React, Tailwind |
| **[`apps/xmpp`](./apps/xmpp)** | **XMPP Server** | Prosody-based XMPP server with custom modules. | Prosody (Lua), Docker, PostgreSQL |
| **[`apps/irc`](./apps/irc)** | **IRC Server** | UnrealIRCd server with Atheme services. | UnrealIRCd (C), Atheme, Docker |

## 🛠️ Getting Started

### Prerequisites

- **Node.js** (LTS recommended)
- **pnpm** (v9.x or later)
- **Docker** & **Docker Compose** (for XMPP and IRC services)

### Installation

Install dependencies for all workspaces:

```bash
pnpm install
```

### 💻 Development

You can start the entire ecosystem in specific modes using Turborepo.

**Start all applications:**
(Note: XMPP and IRC require Docker to be running)
```bash
pnpm run dev
```

**Run specific applications:**

```bash
# Web Application (Next.js)
pnpm --filter web dev

# XMPP Server (Docker)
pnpm --filter xmpp dev

# IRC Server (Docker)
pnpm --filter irc dev
```

### 🏗️ Building

To build all applications for production:

```bash
pnpm run build
```

## 📦 Application Details

### Web (`apps/web`)
The landing page for `atl.chat`. It serves as the main entry point for the project.
- **Port**: `3000` (default)

### XMPP (`apps/xmpp`)
A robust XMPP server powered by Prosody. It supports modern extensions (XEPs) and integrates with the web platform.
- **Ports**: `5222` (c2s), `5269` (s2s), `5280` (http)
- **Commands**: Wraps `make` commands via `package.json` (e.g., `npm run test` -> `make test`).

### IRC (`apps/irc`)
A classic IRC server powered by UnrealIRCd with Atheme services for channel management.
- **Ports**: `6697` (TLS), `6900` (Linking)
- **Services**: NickServ, ChanServ, OperServ

## 🤝 Contributing

1.  Clone the repository.
2.  Install dependencies: `pnpm install`
3.  Create a branch: `git checkout -b feature/my-feature`
4.  Commit changes (conforming to conventional commits).
5.  Push and open a Pull Request.

## 📄 License

MIT License. See individual directories for specific licensing details if applicable.
