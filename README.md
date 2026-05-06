# SwiftDeploy
A declarative infrastructure CLI that generates, deploys, and manages a containerised API service with built-in instrumentation and pre-deployment OPA policy checks from a single manifest.yaml source of truth.

>>>>>>> a55980a (feat: complete Phase 2 with instrumentation, OPA policy checks, and README updates)
## Prerequisites

Docker 24+
Docker Compose v2
Python 3.10+
pip3 install pyyaml jinja2 prometheus_client

## Quick Start

```bash
# 1. Clone the repo
cd swiftdeploy-prod

# 2. Build the app image
docker build -t swift-deploy-1-node:latest ./app

# 3. Make CLI executable
chmod +x swiftdeploy

# 4. Deploy (runs pre-deploy OPA policy check automatically)
./swiftdeploy deploy

# 5. Verify X-Mode Headers
curl -I http://localhost:8080/
```

## Subcommands

| Command | Description |
|---|---|
| `./swiftdeploy init` | Generate nginx.conf + docker-compose.yml from manifest |
| `./swiftdeploy validate` | Run 5 pre-flight checks |
| `./swiftdeploy deploy` | Init + validate + start + wait for health |
| `./swiftdeploy promote canary` | Switch to canary mode |
| `./swiftdeploy promote stable` | Switch back to stable |
| `./swiftdeploy teardown` | Stop everything |
| `./swiftdeploy teardown --clean` | Stop + delete generated configs |

## File Structure

```
swiftdeploy-prod/
├── manifest.yaml          ← Edit this only
├── swiftdeploy            ← CLI executable
├── nginx.conf             ← Auto-generated reverse proxy rules
├── docker-compose.yml     ← Auto-generated multi-container composition
├── history.jsonl          ← Audit trail of metrics collection
├── audit_report.md        ← Generated validation report
├── app/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── policies/
│   ├── infrastructure.rego
│   └── canary_safety.rego
└── templates/
    ├── docker-compose.yml.j2
    └── nginx.conf.j2
```
