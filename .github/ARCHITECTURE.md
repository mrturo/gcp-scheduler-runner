# Architecture Overview

## System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GITHUB ACTIONS (CI/CD)                          │
│                                                                         │
│  1. Push to main branch triggers workflow                              │
│  2. Load secrets: GCP_SA_KEY, GCP_PROJECT_ID, PORT, ENDPOINTS         │
│  3. Run tests & quality checks                                         │
│  4. Build Docker image (Alpine Linux + Flask)                          │
│  5. Security scan with Trivy                                           │
│  6. Push to Artifact Registry                                          │
│  7. Deploy to Cloud Run with env vars from secrets                     │
│                                                                         │
│     Secrets → Environment Variables → Cloud Run Service                │
│     (GitHub)  (Injected at deploy)    (Runtime config)                │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
                        Deployment completes
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD RUN (Deployed Service)                  │
│                                                                         │
│   Service URL: https://gcp-scheduler-runner-xxx-uc.a.run.app          │
│                                                                         │
│   Environment Variables (from GitHub Secrets):                         │
│   • PORT=5000                                                          │
│   • ENDPOINTS=["https://api.example.com/task1", ...]                  │
│                                                                         │
│   Available Endpoints:                                                 │
│   • GET  /              → API documentation                            │
│   • GET  /health        → Health check                                 │
│   • POST /execute       → 🎯 Execute all configured endpoints         │
│   • GET  /task1         → Example task 1                               │
│   • GET  /task2         → Example task 2                               │
│   • GET  /task3         → Example task 3                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↑
                    Invokes /execute endpoint
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                   GOOGLE CLOUD SCHEDULER (Trigger)                      │
│                                                                         │
│   Job Name: gcp-scheduler-runner-job                                   │
│   Schedule: 0 */6 * * * (Every 6 hours)                               │
│   Timezone: UTC (⚠️ NOT local time)                                    │
│                                                                         │
│   Target URL: https://gcp-scheduler-runner-xxx-uc.a.run.app/execute   │
│   Method: POST                                                         │
│   Authentication: OIDC (Service Account)                               │
│                                                                         │
│   Execution Times (UTC):                                               │
│   • 00:00 UTC (12:00 AM)                                              │
│   • 06:00 UTC ( 6:00 AM)                                              │
│   • 12:00 UTC (12:00 PM)                                              │
│   • 18:00 UTC ( 6:00 PM)                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Execute Endpoint

```
Cloud Scheduler sends POST to /execute
            ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         /execute Handler                                │
│                                                                         │
│  1. Load ENDPOINTS from environment variable                           │
│     (Configured via GitHub Secret → Cloud Run env var)                │
│                                                                         │
│  2. Parse endpoint configurations:                                     │
│     • Simple URLs: "https://api.example.com/task1"                    │
│     • Full config: {"url": "...", "method": "POST", ...}              │
│                                                                         │
│  3. Execute endpoints (parallel or sequential):                        │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│     │  Endpoint 1  │  │  Endpoint 2  │  │  Endpoint 3  │            │
│     │  HTTP POST   │  │  HTTP GET    │  │  HTTP PUT    │            │
│     └──────────────┘  └──────────────┘  └──────────────┘            │
│            ↓                  ↓                  ↓                      │
│     ┌──────────────────────────────────────────────────┐              │
│     │      Collect Results (success/failure)           │              │
│     └──────────────────────────────────────────────────┘              │
│                            ↓                                           │
│  4. Return aggregated JSON response:                                  │
│     {                                                                  │
│       "success": true,                                                 │
│       "total_endpoints": 3,                                            │
│       "successful": 3,                                                 │
│       "failed": 0,                                                     │
│       "execution_mode": "parallel",                                    │
│       "results": [...],                                                │
│       "errors": []                                                     │
│     }                                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Configuration Flow

```
Developer → GitHub Repository → GitHub Actions → GCP Artifact Registry → Cloud Run
    │              │                  │                     │                │
    │              │                  │                     │                │
 Commits        Secrets           Workflow             Docker            Service
  code          stored            runs CI/CD            image             running
                                                                          
                                                                    Uses ENDPOINTS
                                                                    from env vars
```

### Configuration Sources by Environment

| Environment | Configuration Source | File/Location |
|-------------|---------------------|---------------|
| **Local Development** | `.env` file | `/Users/a0a11b7/Documents/reps-personal/gcp-scheduler-runner/.env` |
| **GitHub Actions** | GitHub Secrets | `Settings > Secrets and variables > Actions` |
| **Cloud Run (Production)** | Environment Variables | Injected by GitHub Actions during deployment |

**Important**: Production never uses `.env` file. All config comes from GitHub Secrets.

## Timezone Handling

```
Developer's Local Time
         ↓
     (Convert)
         ↓
      UTC Time  ← Cloud Scheduler uses this
         ↓
  Cron Schedule: "0 14 * * 1-5"
         ↓
Cloud Scheduler triggers at UTC time
         ↓
  Cloud Run /execute runs
         ↓
External APIs receive requests
```

### Example: Schedule for 9 AM EST Weekdays

```
Local Time:  9:00 AM EST (UTC-5)
     ↓
Conversion:  9 + 5 = 14:00 UTC
     ↓
Cron:        0 14 * * 1-5
     ↓
Schedule:    "Every weekday at 14:00 UTC"
     ↓
Executes:    Monday-Friday at 9:00 AM EST
```

## Security Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    Security Measures                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GitHub Actions:                                                 │
│  ✓ Secrets stored encrypted                                     │
│  ✓ Trivy vulnerability scanning                                 │
│  ✓ Code quality checks (pylint 10/10)                           │
│  ✓ 100% test coverage requirement                               │
│                                                                  │
│  Docker Image:                                                   │
│  ✓ Alpine Linux (minimal CVEs)                                  │
│  ✓ Non-root user (appuser:1000)                                 │
│  ✓ Multi-stage build (production only deps)                     │
│  ✓ No pip/setuptools in final image                             │
│                                                                  │
│  Cloud Run:                                                      │
│  ✓ Managed platform (auto-patched)                              │
│  ✓ HTTPS only                                                    │
│  ✓ Option for OIDC authentication                               │
│  ✓ IAM role-based access control                                │
│                                                                  │
│  Cloud Scheduler:                                                │
│  ✓ Service account authentication                                │
│  ✓ OIDC token for secure invocation                             │
│  ✓ Audit logs enabled                                            │
└──────────────────────────────────────────────────────────────────┘
```

## Cost Structure

```
Component             Pricing Model          Estimated Cost
─────────────────────────────────────────────────────────────────
GitHub Actions        Free (2000 min/month)  $0
Artifact Registry     Storage + Egress       ~$1-2/month
Cloud Run            Request + Compute       $0 (free tier)
Cloud Scheduler      First 3 jobs free       $0
                     
Total Monthly Cost:                          ~$1-2/month
```

**Free Tier Coverage**:
- Cloud Scheduler: First 3 jobs/month (we use 1)
- Cloud Run: 2M requests + 360,000 GB-seconds/month
- GitHub Actions: 2000 minutes/month

## Parallel vs Sequential Execution

```
PARALLEL MODE (Default):
┌──────────────────────────────────────────────────┐
│ Request: POST /execute                           │
│ {"parallel": true, "max_workers": 5}            │
└──────────────────────────────────────────────────┘
                    ↓
        ┌─────────────────────┐
        │  ThreadPoolExecutor  │
        └─────────────────────┘
         ↓         ↓         ↓
    Endpoint1  Endpoint2  Endpoint3
    (parallel execution)
         ↓         ↓         ↓
        └─────────┬─────────┘
                  ↓
           Collect results
                  ↓
           Return response

Advantages:
• Faster total execution time
• Independent endpoint failures
• Configurable worker pool size

SEQUENTIAL MODE:
┌──────────────────────────────────────────────────┐
│ Request: POST /execute                           │
│ {"parallel": false}                             │
└──────────────────────────────────────────────────┘
                    ↓
              Endpoint 1
                    ↓
              Endpoint 2
                    ↓
              Endpoint 3
                    ↓
           Return response

Advantages:
• Predictable execution order
• One endpoint can use previous results
• Simpler debugging
```

## Monitoring and Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cloud Console:                                             │
│  • Cloud Run logs: Real-time execution logs                │
│  • Cloud Scheduler logs: Job invocation history            │
│  • Cloud Trace: Request latency analysis                   │
│  • Cloud Monitoring: Custom metrics & alerts               │
│                                                             │
│  GitHub:                                                    │
│  • Actions logs: Build & deployment history                │
│  • Security tab: Trivy vulnerability reports               │
│  • Artifacts: Trivy reports (JSON, SARIF, Table)           │
│                                                             │
│  Application:                                               │
│  • /health endpoint: Service health check                  │
│  • Response JSON: Execution results & errors               │
│  • Timestamps: ISO format for all executions               │
└─────────────────────────────────────────────────────────────┘
```

## References

- [GitHub Actions Workflow](.github/workflows/deploy.yml)
- [Cloud Scheduler Setup](.github/CLOUD_SCHEDULER.md)
- [Secrets Configuration](.github/secrets.example)
- [Deployment Guide](.github/README.md)
