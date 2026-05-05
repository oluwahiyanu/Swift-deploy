# SwiftDeploy

A declarative infrastructure CLI that generates, deploys, and manages a
containerised API service from a single `manifest.yaml` source of truth.
screenshots: https://drive.google.com/drive/folders/1eDHp2k1BIqtN-xjNz5T_597Yw6KWkjsS?usp=drive_link
## Prerequisites

- Docker 24+
- Docker Compose v2
- Python 3.10+
- `pip3 install pyyaml jinja2`

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/swiftdeploy-prod.git
cd swiftdeploy-prod

# 2. Build the app image
docker build -t swift-deploy-1-node:latest ./app

# 3. Install Python deps
pip3 install pyyaml jinja2

# 4. Make CLI executable
chmod +x swiftdeploy

# 5. Deploy
./swiftdeploy deploy

# 6. Open the service
curl http://localhost:8080/
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
├── manifest.yaml          ← edit this only
├── swiftdeploy            ← CLI executable
├── nginx.conf             ← auto-generated (project root)
├── docker-compose.yml     ← auto-generated (project root)
├── app/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── templates/
│   ├── nginx.conf.j2
│   └── docker-compose.yml.j2
└── README.md
```
