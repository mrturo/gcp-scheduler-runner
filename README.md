
# GCP Scheduler Runner

Python Flask service that orchestrates multiple HTTP endpoint executions via the `/execute` endpoint. Supports parallel and sequential execution, email notifications, and template-based configuration. See `.github/copilot-instructions.md` for coding and quality policies.

## Features

- **Parallel execution** using `ThreadPoolExecutor` (default, configurable)
- **Sequential execution** mode for controlled workflows
- **Email notifications** with Gmail SMTP and JSON attachments (optional)
- **cURL-like configurations**: HTTP methods, headers, body, query params, timeouts
- **Template variable substitution**: Separate secrets from configuration using `${VAR_NAME}`
- **API key authentication** for protected endpoints
- Mix simple URLs and complex configurations
- Error handling with detailed reporting
- Health check endpoint for monitoring

## Prerequisites

- Python 3.8+ (see `pyproject.toml` and `envtool.sh`)
- pip (Python package manager)
- Gmail account (for email notifications, optional)
- Google Cloud Platform account (for deployment, optional)

## Installation

```bash
# Clone repository
git clone https://github.com/your-username/gcp-scheduler-runner.git
cd gcp-scheduler-runner

bash envtool.sh install [dev|prod]
```

gcp-scheduler-runner/
## Repository Map

```
gcp-scheduler-runner/
├── src/           # Production code (Flask app, config, HTTP, email, auth, models)
├── test/          # Unit tests (100% coverage required)
├── integration/   # Integration tests
├── prompts/       # AI automation prompts for quality enforcement
├── .github/       # CI/CD workflows, deployment, architecture docs
├── envtool.sh     # Development utility script (all workflows)
├── README.md      # Project documentation
```

## Configuration

### Environment Setup

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

echo "API_KEY=your_generated_key_here" >> .env

### API Key Authentication (Optional)

Generate and configure an API key to protect endpoints:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env
echo "API_KEY=your_generated_key_here" >> .env
```

**Protected endpoints** (require `X-API-Key` header when API_KEY is set):
- `/` - Index page
- `/execute` - Main orchestrator endpoint
- `/task1`, `/task2`, `/task3` - Example task endpoints

**Unprotected endpoint**:
- `/health` - Health check

### Template Variable Substitution

Sensitive credentials are referenced in endpoint configuration using `${VAR_NAME}` syntax. See `.env.example` for usage patterns.

### Endpoint Configuration Formats

Endpoints are configured in `.env` as a JSON array. Supports template variables, simple URLs, and mixed formats. See `.env.example` for real examples.

### Email Notifications Setup (Optional)

Configure Gmail SMTP for email notifications. See `.env.example` for required variables and setup instructions.

## Quick Start & Usage

### Start the Server

```bash
bash envtool.sh start
```

Server runs at `http://localhost:3000` by default (configurable via `PORT`).

### Health Check

```bash
curl http://localhost:3000/health
```

### Execute Configured Endpoints

```bash
# Without authentication (if API_KEY not set)
curl -X POST http://localhost:3000/execute

# With authentication (if API_KEY is set)
curl -X POST http://localhost:3000/execute \
  -H "X-API-Key: your_api_key_here"
```

### Execute with Custom Endpoints

See API reference and `.env.example` for supported formats.

### Execution Modes

Parallel execution is default. Use `parallel: false` for sequential mode. See `.github/copilot-instructions.md` for runtime invariants.

### Email Notifications

Add `send_email: true` to request body to receive HTML email reports with JSON attachments. See `.env.example` and `.github/DEPLOYMENT.md` for details.

## API Reference

See `.github/copilot-instructions.md` and `.env.example` for supported endpoint object formats and response structure.

## Development Workflow

Run all checks and tests using `envtool.sh`:

```bash
bash envtool.sh code-check      # Formatting, lint, type, security
bash envtool.sh test            # Unit tests (100% coverage required)
bash envtool.sh quality-gate    # Full quality gate (code + tests)
bash envtool.sh mutation-check  # Mutation testing (when requested)
```

See `.github/copilot-instructions.md` for coding conventions and quality requirements.

docker build -t gcp-scheduler-runner:local .
docker run -p 3000:3000 \
gcloud scheduler jobs create http gcp-scheduler-runner-daily \
## Deployment

See `.github/DEPLOYMENT.md`, `.github/ARCHITECTURE.md`, `.github/CLOUD_SCHEDULER.md`, and `.github/secrets.example` for deployment, CI/CD, and scheduling instructions.

## License

See [LICENSE](LICENSE) file for details..