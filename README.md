# Perseus Dashboard

**Live Context Dashboard for AI Coding Agents** — see exactly what your AI knows about your codebase, in real time.

Built for **H0: Hack the Zero Stack** (June 29, 2026).  
Stack: **Vercel v0** (Next.js frontend) + **AWS Aurora PostgreSQL** (Serverless v2).

## Problem

AI coding agents (Claude Code, Cursor, Copilot, Codex) read stale context files. Your CLAUDE.md goes out of date within hours. You don't know what your agent "knows" — leading to hallucinations, repeated mistakes, and wasted tokens.

## Solution

Perseus Dashboard connects to any project's Perseus context engine and shows:
- **Live service health** — CI, databases, APIs, containers
- **Current context snapshot** — what the agent will see right now
- **Token savings analytics** — how many tokens Perseus saved this week
- **Memory recall feed** — what facts the agent remembered from past sessions

## Architecture

```
┌─────────────────────────────────────┐
│  Vercel / v0.app Frontend           │
│  Next.js 14 + Tailwind + Recharts   │
└────────────┬────────────────────────┘
             │ REST API
┌────────────▼────────────────────────┐
│  FastAPI Backend (Python)           │
│  Context resolution + analytics     │
└────────────┬────────────────────────┘
             │ SQLAlchemy + psycopg2
┌────────────▼────────────────────────┐
│  AWS Aurora PostgreSQL (Serverless) │
│  projects | context_snapshots       │
│  memory_events | token_analytics    │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Provision AWS Aurora PostgreSQL

```bash
# Requires: AWS CLI configured with credentials
bash setup/provision_aurora.sh
```

### 2. Run backend

```bash
cd backend
cp ../.env.example .env
# Edit .env — paste the DATABASE_URL from the provisioning output
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Run frontend

```bash
cd frontend
npm install
NODE_ENV=development npm run dev
# Opens at http://localhost:3000
```

### 4. Deploy to Vercel

```bash
# One-time: vercel login, vercel link
vercel --prod
```

Or connect the GitHub repo to Vercel for auto-deployment.

## Database Schema (Aurora PostgreSQL)

| Table | Purpose |
|---|---|
| `projects` | GitHub URL, name, Perseus config |
| `context_snapshots` | JSONB content, file count, token estimate |
| `memory_events` | Store/recall/decay/insight events + confidence |
| `token_analytics` | Tokens saved per session, total used |

## Hackathon

**H0: Hack the Zero Stack** — $80,000 in prizes | 5,759 participants
- **Required:** Vercel v0 + AWS Database (Aurora / DSQL / DynamoDB)
- **This project:** Vercel (frontend) + AWS Aurora PostgreSQL (backend)
- **Track:** Open Innovation
- **Deadline:** June 29, 2026 @ 5:00 PM PT

## License

MIT — see [LICENSE](LICENSE).
