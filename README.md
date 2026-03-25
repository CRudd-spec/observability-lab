## observability-lab
A local host only observability pipeline built to simulate how real monitoring 
infrastructure generates, routes, and resolves incidents automatically.
Built as a hands-on learning project for integration/automation roles.

## What this does
Runs a full alert-to-ticket pipeline using open source monitoring tools 
and a custom Python webhook. When a metric threshold is breached, the 
pipeline detects it, enriches the alert with operational context, routes 
it to the correct queue based on priority, creates a mock ITSM ticket, 
and resolves it automatically when the condition clears.
Fully automated with no manual intervention required at any stage.

## Stack
| Component | Purpose | Port |
|---|---|---|
| Prometheus | Metrics collection and alert evaluation | 9090 |
| Grafana | Dashboard and visualization | 3000 |
| Alertmanager | Alert routing and webhook dispatch | 9093 |
| Node Exporter | Host system metrics (CPU, RAM, disk) | 9100 |
| Loki | Log aggregation and storage | 3101 |
| Promtail | Log collection agent — scrapes Docker containers via socket | — |
| webhook.py | Alert enrichment, deduplication, routing | 5001 |
| mock_itsm.py | Simulated ITSM ticket system with browser UI | 5002 |
| ServiceNow | Enterprise ITSM incident creation | External |
| Ollama + Mistral | Local LLM enrichment (summary, likely cause, severity) | 11434 |

## Pipeline flow

**Metrics and alerting:**
```
Node Exporter → Prometheus → Alertmanager → webhook.py → External Platforms
  (metrics)      (evaluate)    (route)       (enrich)     (ticket)
```

**Log pipeline:**
```
Docker containers → Promtail → Loki → Grafana
   (stdout/stderr)  (collect)  (store)  (query)
```

1. Node Exporter exposes host metrics
2. Prometheus scrapes every 15 seconds and evaluates alert rules
3. When a rule fires, Prometheus hands the alert to Alertmanager
4. Alertmanager POSTs the payload to the Flask webhook on the host
5. webhook.py enriches the alert with operational context, calls local Ollama/Mistral for AI-generated summary, likely cause, and suggested severity, then routes based on priority.
6. Ticket is created in mock_itsm.py (local) or ServiceNow (external) depending on routing config
7. pagerduty.py currently points to mock_itsm but is intended to be similar to servicenow.py with access to the platform.

## Log pipeline
Promtail collects container logs by connecting to the Docker socket (`/var/run/docker.sock`) using Docker service discovery. It polls for running containers every 5 seconds and tails their stdout/stderr streams directly from `/var/lib/docker/containers`.

**Label enrichment via Docker service discovery:**
Each log line is labelled automatically from container metadata before being shipped to Loki:
- `container` — the container name (e.g. `prometheus`, `alertmanager`)
- `stream` — stdout or stderr
- `service` — the Docker Compose service name

This means in Grafana you can filter logs by `{service="webhook"}` or `{container="loki"}` without any manual configuration. Loki stores the logs on disk under a named volume (`loki-data`) and is queryable from Grafana using LogQL.

> Note: Loki runs as `user: "0"` (root) in this lab to allow WAL and compactor directory creation on the named volume. Do not use this in production.

---
## Example Alert rules
| Alert | Metric | Threshold | Severity | Priority |
|---|---|---|---|---|
| HighCPUUsage | CPU % | > 10 | warning | P2 |
| HighRAMUsage | RAM % | > 10 | critical | P1 |

Note that thresholds are intentionally low for lab testing.

## Key features
**Enrichment**
webhook.py adds priority, runbook URL, and timestamp to every raw 
Alertmanager payload before forwarding it.
**Deduplication**
Alerts are deduplicated using the Prometheus-generated fingerprint field. 
Fingerprints are persistently accessible via disk in `seen_fingerprints.json` so 
deduplication survives webhook restarts.
**Priority-based routing**
- P1 (critical) → `/tickets/critical`
- P2 (warning) → `/tickets/standard`
- Unknown priority → `/tickets/standard` with a warning logged
**Resolution handling**
When Alertmanager sends a resolved payload, the webhook clears the 
fingerprint and notifies mock_itsm to close the ticket. The ticket moves 
from the open table to the resolved table in the browser UI.
**AI Enrichment**
Before ticket creation, webhook.py calls a locally hosted Mistral LLM 
via Ollama to generate a plain-language summary, likely cause, and 
suggested severity for each alert. Runs entirely on-device with no 
external API calls or data leaving the machine.
---
## Running it
**Start the Docker stack:**
```bash
cd ~/lab
sudo docker-compose up -d
```
**Start the webhook and mock ITSM (separate terminals, venv is used):**
```bash
source ~/lab/venv/bin/activate
python webhook.py
```
```bash
source ~/lab/venv/bin/activate
python mock_itsm.py
```
**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093
- Mock ITSM: http://localhost:5002
---
## Known limitations
- ServiceNow resolution handling not yet implemented and alerts resolve in 
  mock ITSM but ServiceNow incidents are not automatically closed
- Mock ITSM state is in-memory only and restarting mock_itsm.py clears 
  all tickets
- Fingerprint dedup is persistent but if the same alert fires after 
  resolving, it will re-ticket correctly...however mock_itsm has no 
  concept of incident history beyond the current session
- No authentication on any endpoint
- Single node only alerting
- LLM enrichment adds latency per alert (~5-15 seconds on CPU). Falls back gracefully if Ollama is unavailable.
---
## Related project
Alert-Enrichment-Engine covers the same enrichment and deduplication 
logic in pure Python. This repo is what it looks like when that logic 
runs inside a real monitoring pipeline.
