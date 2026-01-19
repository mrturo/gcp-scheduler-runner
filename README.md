
# GCP Scheduler Runner

Python Flask service that orchestrates multiple HTTP endpoint executions through a main `/execute` endpoint. Supports parallel and sequential execution with email notifications.

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

- Python 3.8 or higher
- pip (Python package manager)
- Gmail account (for email notifications, optional)
- Google Cloud Platform account (for deployment, optional)

## Installation

```bash
# Clone repository
git clone https://github.com/your-username/gcp-scheduler-runner.git
cd gcp-scheduler-runner

# Install dependencies
pip install -r requirements.txt

# Or use envtool.sh (creates virtual environment)
bash envtool.sh install
```

## Project Structure

```
gcp-scheduler-runner/
├── src/                   # Source code
│   ├── app.py             # Flask application and endpoints
│   ├── config.py          # Configuration and template substitution
│   ├── http_executor.py   # HTTP execution logic
│   ├── email_service.py   # Email notification service
│   ├── auth.py            # API key authentication
│   └── models.py          # Data models and response formatting
├── test/                  # Unit tests (100% coverage)
├── integration/           # Integration tests
├── prompts/               # AI agent automation prompts
├── .github/               # CI/CD workflows and deployment docs
├── envtool.sh             # Development utility script
└── README.md              # This file
```

## Configuration

### Environment Setup

Create a `.env` file from the example:

```bash
cp .env.example .env
```

### API Key Authentication (Optional)

Generate and configure an API key to protect endpoints:

```bash
# Generate secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
echo "API_KEY=your_generated_key_here" >> .env
```

**Protected endpoints** (require `X-API-Key` header when API_KEY is set):
- `/` - Index page with configuration info
- `/execute` - Main orchestrator endpoint
- `/task1`, `/task2`, `/task3` - Example task endpoints

**Unprotected endpoints**:
- `/health` - Health check (for monitoring/load balancers)

### Template Variable Substitution

Separate sensitive credentials from endpoint structure using `${VAR_NAME}` syntax:

```bash
# .env file

# Sensitive credentials - KEEP SECRET
ENDPOINT_API_KEY=sk_test_51H8zXSGG7wYpQ2K7...
EXTERNAL_SERVICE_TOKEN=bearer_abc123def456...

# Endpoint configuration - Reference variables with ${VAR_NAME}
# This structure can be safely committed to .env.example
ENDPOINTS='[
  {
    "url": "https://api.example.com/sync",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer ${ENDPOINT_API_KEY}"
    }
  },
  {
    "url": "https://external-api.example.com/data",
    "method": "GET",
    "headers": {
      "X-API-Key": "${EXTERNAL_SERVICE_TOKEN}"
    }
  }
]'
```

**Benefits**:
- ✅ Endpoint structure safely committed to version control
- ✅ Secrets stored separately as individual variables
- ✅ Compatible with GitHub Secrets and CI/CD
- ✅ Clear error messages for missing variables

### Endpoint Configuration Formats

Configure endpoints in `.env` using one of these formats:

**1. With template variables (RECOMMENDED)**:
```bash
API_TOKEN=your_secret_token
SERVICE_URL=https://api.example.com

ENDPOINTS='[
  {
    "url": "${SERVICE_URL}/users",
    "method": "POST",
    "headers": {"Authorization": "Bearer ${API_TOKEN}"},
    "json": {"name": "John"}
  }
]'
```

**2. Simple URLs**:
```bash
ENDPOINT_1=http://localhost:3000/task1
ENDPOINT_2=http://localhost:3000/task2
```

**3. Mixed formats**:
```bash
SECRET_KEY=my_secret_xyz

ENDPOINT_1=http://simple-url.com/endpoint
ENDPOINT_2={"url": "https://api.example.com", "headers": {"X-API-Key": "${SECRET_KEY}"}}
```

### Email Notifications Setup (Optional)

Configure Gmail SMTP for email notifications:

**1. Enable 2-Step Verification**:
   - Visit [https://myaccount.google.com/security](https://myaccount.google.com/security)
   - Enable "2-Step Verification"

**2. Generate App Password**:
   - Visit [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Other (Custom name)"
   - Copy the 16-character password

**3. Add to `.env`**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

## Usage

### Start the Server

```bash
# Using envtool.sh (recommended)
bash envtool.sh start

# Or directly
python src/app.py
```

Server runs at `http://localhost:3000` by default.

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

**Simple URLs**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "endpoints": [
      "http://localhost:3000/task1",
      "http://localhost:3000/task2"
    ]
  }'
```

**Full cURL-like configuration**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "endpoints": [
      {
        "url": "https://api.example.com/users",
        "method": "POST",
        "headers": {
          "Authorization": "Bearer token123",
          "Content-Type": "application/json"
        },
        "json": {"name": "John", "email": "john@example.com"},
        "timeout": 30
      },
      {
        "url": "https://api.example.com/orders",
        "method": "GET",
        "params": {"status": "active", "limit": 10}
      }
    ]
  }'
```

### Execution Modes

**Parallel execution (default)**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": ["http://localhost:3000/task1", "http://localhost:3000/task2"],
    "parallel": true,
    "max_workers": 10
  }'
```

**Sequential execution**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": ["http://localhost:3000/task1", "http://localhost:3000/task2"],
    "parallel": false
  }'
```

**Parameters**:
- `parallel` (boolean, default: `true`): Enable parallel execution
- `max_workers` (integer, default: `min(10, num_endpoints)`): Max concurrent workers
- `send_email` (boolean, default: `false`): Send email notification after execution

### Email Notifications

Add `"send_email": true` to receive HTML email reports with JSON attachments:

```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "endpoints": ["https://api.example.com/task"],
    "send_email": true
  }'
```

**Email includes**:
- Success/failure status (✅/❌)
- Total, successful, and failed counts
- Execution mode (parallel/sequential)
- **JSON attachments**: One `.json` file per endpoint with complete response data
- Error details for failed executions

## API Reference

### Endpoint Object Format

Each endpoint can be:

**1. Simple URL** (string):
```json
"http://example.com/api"
```

**2. Full configuration** (object):
```json
{
  "url": "https://api.example.com/endpoint",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer token",
    "Content-Type": "application/json"
  },
  "json": {...},
  "body": "raw data",
  "params": {"key": "value"},
  "timeout": 30
}
```

**Supported fields**:
- `url` (required): Endpoint URL
- `method` (optional): GET, POST, PUT, DELETE, PATCH (default: POST)
- `headers` (optional): HTTP headers dictionary
- `json` (optional): Request body as JSON object
- `body` (optional): Request body as raw string
- `params` (optional): Query parameters dictionary
- `timeout` (optional): Timeout in seconds (default: 30)

### Response Format

**Success response**:
**Success response**:
```json
{
  "success": true,
  "total_endpoints": 3,
  "successful": 3,
  "failed": 0,
  "execution_mode": "parallel",
  "results": [...],
  "errors": [],
  "email_notification": {
    "email_sent": true,
    "recipient": "admin@example.com",
    "from": "notifications@example.com",
    "attachments": 3
  }
}
```

## Development

### Running Tests

**Unit tests** (fast, mocked dependencies):
```bash
bash envtool.sh test
```

**Integration tests** (requires running server):
```bash
# Start server in separate terminal
bash envtool.sh start

# Run integration tests
source .venv/bin/activate
pytest integration/ -v
```

**Test coverage**: 100% line coverage for all source code in `src/`.

**Coverage includes**:
- All endpoints and request execution modes
- Email notifications with attachments
- Template variable resolution
- Error handling and edge cases

### Code Quality

Run quality checks:
```bash
bash envtool.sh code-check
```

**Includes**:
- **Formatting**: Black + isort
- **Linting**: Pylint (score 10.0 required)
- **Type checking**: mypy (zero errors)
- **Security scanning**: Trivy

### Full Quality Gate

Validate both code quality and tests:
```bash
bash envtool.sh quality-gate
```

Runs `code-check` + `test` and validates both pass.

### Mutation Testing

Ensure test suite robustness:
```bash
bash envtool.sh mutation-check
```

### AI Automation Prompts

The `prompts/` directory contains specialized prompts for AI coding agents (like GitHub Copilot) to automate quality enforcement:

- **`code-check.md`**: Automates fixing code quality issues (formatting, linting, type checking, security)
- **`test.md`**: Automates fixing test failures and achieving 100% coverage
- **`quality-gate.md`**: Runs both code-check and test in a loop until both pass
- **`mutation-check.md`**: Automates killing surviving mutants to strengthen tests
- **`test-optimization.md`**: Optimizes test suite performance and structure
- **`english-code-enforcer.md`**: Ensures all code/comments/docs use English

**Usage**: Share the relevant prompt with your AI coding agent when you need automated fixes. These prompts operate in "run-to-completion" mode, applying minimal safe changes until the quality gate passes.

## Deployment

### Docker Testing

Test Docker build locally:
```bash
# Build image
docker build -t gcp-scheduler-runner:local .

# Run with authentication
docker run -p 3000:3000 \
  -e ENDPOINTS='["http://example.com/api"]' \
  -e API_KEY='your_api_key_here' \
  gcp-scheduler-runner:local

# Test
curl http://localhost:3000/health
curl -X POST http://localhost:3000/execute -H "X-API-Key: your_api_key_here"
```

### Google Cloud Run Deployment

Complete CI/CD pipeline for automated deployment.

**Quick start**:

1. **Configure GitHub Secrets** (see [.github/DEPLOYMENT.md](.github/DEPLOYMENT.md)):
   - `GCP_SA_KEY`: Service Account JSON key
   - `GCP_PROJECT_ID`: GCP Project ID
   - `PORT`: Application port (e.g., `3000`)
   - `API_KEY`: API key for authentication
   - `ENDPOINTS`: Endpoint configurations (JSON array)

2. **One-time GCP setup**:
   ```bash
   # Create Artifact Registry repository
   gcloud artifacts repositories create gcp-scheduler-runner \
     --repository-format=docker \
     --location=us-central1 \
     --description="Docker repository for gcp-scheduler-runner"

   # Disable vulnerability scanning (cost control)
   gcloud artifacts repositories update gcp-scheduler-runner \
     --location=us-central1 \
     --disable-vulnerability-scanning
   ```

3. **Push to main branch** - GitHub Actions handles the rest

### Cloud Scheduler Setup

Configure scheduled execution:

```bash
# Daily execution at 4:30 AM UTC with parallel mode and email
gcloud scheduler jobs create http gcp-scheduler-runner-daily \
  --location=us-central1 \
  --schedule="30 4 * * *" \
  --uri="https://YOUR-SERVICE-URL.run.app/execute" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-API-Key=YOUR_API_KEY" \
  --message-body='{"parallel": true, "max_workers": 10, "send_email": true}' \
  --attempt-deadline=300s \
  --max-retry-attempts=3
```

⚠️ **Timezone**: Cloud Scheduler uses UTC. Convert your local time accordingly.

**Chile timezone examples**:
- 4:30 AM UTC → 1:30 AM Chile (summer) / 12:30 AM Chile (winter)
- 7:00 AM UTC → 4:00 AM Chile (summer) / 3:00 AM Chile (winter)

### Deployment Documentation

- [Architecture Overview](.github/ARCHITECTURE.md)
- [GitHub Actions Setup](.github/DEPLOYMENT.md)
- [Cloud Scheduler Guide](.github/CLOUD_SCHEDULER.md)
- [Secrets Configuration](.github/secrets.example)

## License

See [LICENSE](LICENSE) file for details.