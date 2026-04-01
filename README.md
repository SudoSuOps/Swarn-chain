# SwarmChain

**Distributed Reasoning Ledger — a contribution-aware search system.**

Search becomes data. Elimination becomes integrity. Finality creates value.

---

SwarmChain is a block-based search engine where nodes submit *attempts*, not answers. Attempts are scored, pruned, traced, and promoted. When a solution reaches finality, the block is sealed as a high-integrity dataset artifact.

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for local dev)
- Node.js 20+ (for frontend dev)

### Run with Docker Compose

```bash
# Start all services (postgres, redis, backend, frontend)
make up

# Check health
curl http://localhost:8000/health

# Run the node simulator
python simulator/simulator.py --rounds 20

# Open the block explorer
open http://localhost:3000

# View logs
make logs

# Stop
make down
```

### Local Development

```bash
# Start Postgres + Redis only
docker compose -f infra/docker-compose.yml up -d postgres redis

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Run backend (auto-creates tables)
make dev

# Run tests
make test

# Install frontend dependencies
cd frontend && npm install && npm run dev
```

## Architecture

```
Nodes → Attempt Gateway → Verifier → Controller → Reward Engine
                                         ↓
                                   Finality Service
                                         ↓
                                   Sealed Block Artifact
```

- **Controller**: orchestrates blocks, prunes weak candidates, promotes strong ones
- **Verifier**: deterministic scoring (ARC exact grid match for MVP)
- **Reward Engine**: 40% solver / 30% lineage / 20% exploration / 10% efficiency
- **Lineage Store**: tracks parent-child attempt graph
- **Block Explorer**: React dashboard for real-time monitoring

See [docs/architecture.md](docs/architecture.md) for full details.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /blocks/open | Open a new reasoning block |
| GET | /blocks | List all blocks |
| GET | /blocks/{id} | Get block detail |
| POST | /blocks/{id}/finalize | Trigger finalization |
| GET | /blocks/{id}/artifacts | Get sealed artifacts |
| POST | /attempts | Submit a reasoning attempt |
| GET | /attempts/{id} | Get attempt detail |
| GET | /attempts/block/{id} | List block attempts |
| GET | /attempts/block/{id}/top | Top-scoring attempts |
| GET | /attempts/block/{id}/lineage | Lineage graph |
| POST | /nodes/register | Register a compute node |
| GET | /nodes | List nodes |
| GET | /nodes/{id}/stats | Node performance stats |
| GET | /blocks/{id}/rewards | Reward breakdown |
| GET | /health | Health check |
| GET | /metrics | System metrics |

## MVP Domain: ARC

The MVP uses ARC-style deterministic grid tasks. Verification is exact — no model opinion needed.

8 sample tasks included: fill, mirror, rotate, swap, border, transpose, invert, scale.

The architecture is scaffolded for future domains (CRE, Legal, Capital Markets) via the `DomainVerifier` interface.

## Node Simulator

Simulates 4 node types with different capabilities:
- **jetmini**: cheap, fast, random exploration (edge compute)
- **zima-lowgpu**: structured transforms (mirror, swap, invert)
- **mid-gpu**: multi-step transforms (rotate, transpose, scale, border)
- **queen**: refinement only — derives from promoted parents

## Project Structure

```
swarmchain/
  backend/
    swarmchain/
      api/          # FastAPI route handlers
      db/           # SQLAlchemy models + engine
      schemas/      # Pydantic request/response schemas
      services/     # Core logic (controller, verifier, rewards, lineage)
      tasks/        # ARC task catalog
      main.py       # FastAPI app entry
      config.py     # Centralized settings
  simulator/        # Node simulation for testing
  frontend/         # React block explorer
  infra/            # Docker Compose + env config
  tests/            # pytest suite (48 tests)
  docs/             # Architecture + walkthrough
```

## Tests

```bash
make test
# 48 tests: verifier, blocks, attempts, rewards, integration
```

---

## Swarm & Bee Repositories

| Repo | Purpose |
|------|---------|
| **[Swarn-chain](https://github.com/SudoSuOps/Swarn-chain)** | SwarmChain implementation — backend, explorer, tests (this repo) |
| **[glass-wall](https://github.com/SudoSuOps/glass-wall)** | Architecture vision, doctrine, operational philosophy |
| **[SwarmOS](https://github.com/SudoSuOps/SwarmOS)** | The operating system — flight sheets, GPU benchmarks, POJ, cost-to-mint |

---

*SwarmChain — where search becomes data, elimination becomes integrity, and finality creates value.*

*Part of [Swarm & Bee](https://github.com/SudoSuOps/glass-wall) — Defendable Commercial Compute Intelligence Refinery*
