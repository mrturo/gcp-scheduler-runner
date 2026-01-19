
# GCP Scheduler Runner

Python Flask project that executes multiple endpoints in sequence, orchestrated
by a main `/execute` endpoint.

## Features

- Main endpoint `/execute` that orchestrates multiple endpoints
- **Parallel execution** using `ThreadPoolExecutor` (default behavior, configurable)
- **Sequential execution** mode available for controlled workflows
- **Email notifications** with Gmail SMTP after each execution (optional)
- Support for cURL-like endpoint configurations: HTTP methods, headers, body, query params, timeouts
- Support for simple URL strings (backwards compatible)
- Mix simple and complex configurations in the same run
- Configurable `max_workers` for parallel execution control
- Error handling and detailed reporting with execution mode info
- Example endpoints included for testing
- Health check endpoint

## Endpoint Configuration Format

Each endpoint can be one of the following:

1. Simple URL (string): `"http://example.com/api"`
2. Full configuration (object):

```json
{
  "url": "https://api.example.com/endpoint",
  "method": "POST",           // GET, POST, PUT, DELETE, PATCH (default: POST)
  "headers": {
    "Authorization": "Bearer token",
    "Content-Type": "application/json"
  },
  "json": {...},               // Body as JSON
  "body": "raw data",        // Or body as raw string
  "params": {                  // Query parameters
    "key": "value"
  },
  "timeout": 30                // Timeout in seconds (default: 30)
}
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
gcp-scheduler-runner/
├── src/                    # Source code
│   ├── app.py             # Flask application
│   └── config.py          # Configuration utilities
├── test/                   # Unit tests (mocked)
│   ├── test_app.py        # App functionality tests
│   └── test_email.py      # Email notification tests
├── integration/            # Integration tests (require running server)
│   └── test_endpoints.py  # End-to-end API tests
├── envtool.sh             # Development utility script
└── README.md              # Documentation
```

## Usage

### Start the server

```bash
# Using envtool.sh (recommended)
bash envtool.sh start

# Or directly
python src/app.py
```

Server will run at `http://localhost:3000` by default.

### Authentication

**If `API_KEY` is configured** in your `.env` file, all requests (except `/health`) must include the `X-API-Key` header:

```bash
# Generate a secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env file
echo "API_KEY=your_generated_key_here" >> .env
```

**Protected endpoints**:
- `/` - Index page with configured endpoints information
- `/execute` - Main orchestrator endpoint
- `/task1`, `/task2`, `/task3` - Example task endpoints

**Unprotected endpoints**:
- `/health` - Health check endpoint (for monitoring and load balancers)

**If `API_KEY` is not set**, the service allows unauthenticated requests to all endpoints (useful for local development).

### Execute endpoints (option 1 - configured endpoints)

```bash
# Without authentication (if API_KEY not set)
curl -X POST http://localhost:3000/execute

# With authentication (if API_KEY is set)
curl -X POST http://localhost:3000/execute \
  -H "X-API-Key: your_api_key_here"
```

### Execute endpoints (option 2 - simple URLs)

```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "endpoints": [
      "http://localhost:3000/task1",
      "http://localhost:3000/task2"
    ],
    "default_payload": {
      "user_id": 123,
      "action": "test"
    }
  }'
```

### Execute endpoints (option 3 - full cURL-like configuration)

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
        "json": {
          "name": "John",
          "email": "john@example.com"
        },
        "timeout": 30
      },
      {
        "url": "https://api.example.com/orders",
        "method": "GET",
        "headers": {
          "Authorization": "Bearer token123"
        },
        "params": {
          "status": "active",
          "limit": 10
        }
      },
      {
        "url": "https://api.example.com/webhooks",
        "method": "PUT",
        "headers": {
          "X-API-Key": "secret123"
        },
        "body": "raw string data"
      }
    ]
  }'
```

### Mix simple URLs and complex configurations

```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": [
      "http://simple-url.com/endpoint",
      {
        "url": "https://complex.com/api",
        "method": "POST",
        "headers": {"Authorization": "Bearer xyz"},
        "json": {"data": "value"}
      }
    ],
    "default_payload": {
      "applies_to": "simple URLs only"
    }
  }'
```

### Parallel Execution (NEW)

By default, endpoints are executed **in parallel** using `ThreadPoolExecutor`. This significantly reduces total execution time for multiple endpoints.

**Parallel execution (default)**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": [
      "http://localhost:3000/task1",
      "http://localhost:3000/task2",
      "http://localhost:3000/task3"
    ],
    "parallel": true,
    "max_workers": 10
  }'
```

**Sequential execution (original behavior)**:
```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": [
      "http://localhost:3000/task1",
      "http://localhost:3000/task2"
    ],
    "parallel": false
  }'
```

**Parameters**:
- `parallel` (boolean, default: `true`): Enable parallel execution
- `max_workers` (integer, default: `min(10, num_endpoints)`): Maximum number of concurrent workers
- `send_email` (boolean, default: `false`): Send email notification after execution

**Response includes execution mode**:
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

**Notes**:
- Parallel execution is ideal for I/O-bound HTTP requests
- Order of execution is not guaranteed in parallel mode
- Single endpoint requests automatically use sequential mode

## Email Notifications

Send HTML email reports after each execution via Gmail SMTP.

### Setup Gmail SMTP

1. **Enable 2-Step Verification** in your Google Account:
   - Go to [https://myaccount.google.com/security](https://myaccount.google.com/security)
   - Enable "2-Step Verification"

2. **Generate App Password**:
   - Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Other (Custom name)"
   - Copy the 16-character password

3. **Configure environment variables** in `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   EMAIL_FROM=your-email@gmail.com
   EMAIL_TO=recipient@example.com
   ```

### Usage

Add `"send_email": true` to your request:

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
- ✅/❌ Success/Failure status
- Total, successful, and failed endpoint counts
- Execution mode (parallel/sequential)
- Detailed results for each endpoint (as HTML)
- Error details if any failures occurred
- **📎 JSON file attachments**: Each endpoint result attached as separate `.json` file

**JSON Attachments**:
- **One JSON file per endpoint result**
- Filename format: `01_api_example_com_users_result.json` (for successful executions)
- Error format: `ERROR_01_api_example_com_orders.json` (for failed executions)
- Contains complete endpoint response data: URL, method, status code, headers, response body, timestamp
- Easy to process programmatically or archive for auditing
- Filenames sanitized: URLs converted to safe filesystem names (max 50 chars)

**Notes**:
- Emails are sent **only if** `send_email: true` is in the request
- If SMTP credentials are not configured, execution continues without email
- Email sent from your personal Gmail (appears in your "Sent" folder)
- Free and unlimited for personal use
- JSON attachments included automatically (no additional configuration needed)
- Error handling works the same in both modes

### Health Check

```bash
curl http://localhost:3000/health
```

## Tests

### Unit Tests (Recommended)

Run fast unit tests with mocked dependencies:

```bash
bash envtool.sh test
```

Or run manually:

```bash
source .venv/bin/activate
pytest test/ -v --cov=src --cov-report=term-missing
```

### Integration Tests (Optional)

Run end-to-end tests against a running server:

```bash
# 1. Start the server in another terminal
bash envtool.sh start

# 2. Run integration tests
source .venv/bin/activate
pytest integration/ -v
```

### Test Coverage

The project maintains **100% test coverage** of the core logic:

**Unit Tests** (`test/`):
- **test_app.py**: All endpoints, request execution, validation, error handling
- **test_email.py**: Email notification functionality with Gmail SMTP

**Integration Tests** (`integration/`):
- **test_endpoints.py**: End-to-end API testing against live server

**Coverage includes**:
- All endpoints (/, /health, /task1, /task2, /task3, /execute)
- Parallel and sequential execution modes  
- Email notifications with JSON attachments
- Template variable resolution
- Error handling and edge cases

## Configuration

Endpoints are configured via the `.env` file. Create one from the example:

```bash
cp .env.example .env
```

### 🔐 Separating Sensitive Data with Template Variables

**NEW**: Use template variable substitution to separate sensitive credentials from endpoint structure using `${VAR_NAME}` syntax.

**Benefits**:
- ✅ `ENDPOINTS` structure can be safely committed to version control (.env.example)
- ✅ Secrets stored in separate environment variables
- ✅ Easy to audit what is sensitive and what is not
- ✅ Compatible with GitHub Secrets (each secret as individual variable)

**Example**:

```bash
# .env file

# Sensitive credentials - KEEP THESE SECRET
ENDPOINT_API_KEY=sk_test_51H8zXSGG7wYpQ2K7...
EXTERNAL_SERVICE_TOKEN=bearer_abc123def456...
DATABASE_PASSWORD=super_secret_password

# Endpoint configuration - uses ${VAR_NAME} for sensitive data
# This structure can be committed to .env.example
ENDPOINTS='[
  {
    "url": "https://api.domain.com/sync",
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

**How it works**:
1. Define your secrets as individual environment variables
2. Reference them in `ENDPOINTS` using `${VARIABLE_NAME}` syntax
3. At runtime, placeholders are replaced with actual values from environment
4. If a referenced variable is missing, you get a clear error message

### ENDPOINTS formats in `.env`

You can provide endpoints as:

1. **With template variables (RECOMMENDED)**:

```bash
# Define secrets separately
API_TOKEN=your_secret_token_here
SERVICE_URL=https://api.example.com

# Reference them in ENDPOINTS
ENDPOINTS='[
  {
    "url": "${SERVICE_URL}/users",
    "method": "POST",
    "headers": {"Authorization": "Bearer ${API_TOKEN}"},
    "json": {"name": "John"}
  }
]'
```

2. **Simple URLs** (no sensitive data):

```bash
ENDPOINT_1=http://localhost:3000/task1
ENDPOINT_2=http://localhost:3000/task2
```

3. **Full JSON configuration** (direct values, not recommended for secrets):

```bash
ENDPOINT_1={"url": "https://api.example.com/users", "method": "POST", "headers": {"Authorization": "Bearer token123"}, "json": {"name": "John"}}
ENDPOINT_2={"url": "https://api.example.com/orders", "method": "GET", "params": {"status": "active"}}
```

4. **Mix formats**:

```bash
SECRET_KEY=my_secret_key_xyz

ENDPOINT_1=http://simple-url.com/endpoint
ENDPOINT_2={"url": "https://complex.com/api", "method": "POST", "headers": {"X-API-Key": "${SECRET_KEY}"}}
ENDPOINT_3=http://another-simple-url.com/api
```

Endpoints are executed in defined order (ENDPOINT_1, ENDPOINT_2, ...).

## Project Structure

- `app.py` - Main application and endpoints
- `config.py` - Configuration helpers
- `test_app.py` - Pytest test suite
- `test_endpoints.py` - Manual/legacy test script
- `requirements.txt` - Project dependencies
- `requirements-dev.txt` - Dev dependencies (pytest, black, pylint, etc.)
- `envtool.sh` - Utility script (install, test, code-check, start, etc.)
- `.env.example` - Example environment variables

## Quality

Run quality checks with:

```bash
bash envtool.sh code-check
```

**Includes**:
- **Formatting**: Black + isort
- **Linting**: Pylint + autoflake
- **Type checking**: mypy
- **Security scanning**: Trivy (vulnerabilities, misconfigurations, secrets)

Run tests separately with:

```bash
bash envtool.sh test
```

## Response Format

The `/execute` endpoint returns:

```json
{
  "success": true,
  "total_endpoints": 3,
  "successful": 3,
  "failed": 0,
  "results": [...],
  "errors": []
}
```

## Deployment to Google Cloud Run

This project includes a complete CI/CD pipeline for automated deployment to Google Cloud Run.

**🎯 Key Points**:
- **All configuration** comes from GitHub Secrets (no `.env` in production)
- **Cloud Scheduler** invokes the `/execute` endpoint (POST)
- **Timezone**: Cloud Scheduler uses **UTC** (convert your local time)

### Quick Deploy

1. **Configure GitHub Secrets** (see [.github/README.md](.github/README.md))
   - `GCP_SA_KEY`: Service Account JSON key
   - `GCP_PROJECT_ID`: Your GCP Project ID
   - `PORT`: Application port (e.g., `3000`)
   - `API_KEY`: API key for X-API-Key authentication (generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` )
   - `ENDPOINTS`: Endpoint configurations (JSON array)

2. **One-time GCP Setup**
   ```bash
   # Create Artifact Registry repository
   gcloud artifacts repositories create gcp-scheduler-runner \
     --repository-format=docker \
     --location=us-central1 \
     --description="Docker repository for gcp-scheduler-runner service"
   
   # Disable vulnerability scanning (cost control)
   gcloud artifacts repositories update gcp-scheduler-runner \
     --location=us-central1 \
     --disable-vulnerability-scanning
   ```

3. **Push to main branch**
   ```bash
   git push origin main
   ```

The GitHub Actions workflow will:
- Run tests and quality checks
- Build and scan Docker image for vulnerabilities
- Push image to Google Artifact Registry
- Deploy to Cloud Run automatically

### Scheduled Execution with Cloud Scheduler

After deployment, set up Cloud Scheduler to trigger the service periodically:

**🎯 Cloud Scheduler invokes the `/execute` endpoint**:
- **URL**: `https://YOUR-SERVICE-URL.run.app/execute`
- **Method**: POST (recommended) or GET
- **Timezone**: ⚠️ **UTC** (convert your local time to UTC)
- **Authentication**: Must include `X-API-Key` header

```bash
# Execute daily at 4:30 AM UTC (early morning in Chile) with parallel execution and email notifications
gcloud scheduler jobs create http gcp-scheduler-runner-chile \
  --location=us-central1 \
  --schedule="30 4 * * *" \
  --uri="https://gcp-scheduler-runner-646185261155.us-central1.run.app/execute" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-API-Key=YOUR_API_KEY_HERE,X-Scheduler-Trigger=true" \
  --message-body='{
    "parallel": true,
    "max_workers": 10,
    "send_email": true
  }' \
  --attempt-deadline=300s \
  --max-retry-attempts=3 \
  --description="Executes configured endpoints daily at 4:30 AM UTC with parallel execution and email notifications"
```

**Timezone Conversion Examples for Chile**:
- **4:30 AM UTC** → 1:30 AM Chile (verano) / 12:30 AM Chile (invierno) ⭐ **RECOMENDADO**
- **5:00 AM UTC** → 2:00 AM Chile (verano) / 1:00 AM Chile (invierno)  
- **6:00 AM UTC** → 3:00 AM Chile (verano) / 2:00 AM Chile (invierno)
- **7:00 AM UTC** → 4:00 AM Chile (verano) / 3:00 AM Chile (invierno)

See [.github/CLOUD_SCHEDULER.md](.github/CLOUD_SCHEDULER.md) for complete setup guide with timezone conversion table.

### Local Docker Testing

Test the Docker build locally before deployment:

```bash
# Build image
docker build -t gcp-scheduler-runner:local .

# Run container (without authentication)
docker run -p 3000:3000 \
  -e ENDPOINTS='["http://example.com/api"]' \
  gcp-scheduler-runner:local

# Run container (with authentication)
docker run -p 3000:3000 \
  -e ENDPOINTS='["http://example.com/api"]' \
  -e API_KEY='your_api_key_here' \
  gcp-scheduler-runner:local

# Test endpoints
curl http://localhost:3000/health
curl -X POST http://localhost:3000/execute -H "X-API-Key: your_api_key_here"
```

### Deployment Documentation

- [Architecture Overview](.github/ARCHITECTURE.md) - System flow & configuration sources
- [GitHub Actions Pipeline Setup](.github/README.md) - CI/CD configuration
- [Cloud Scheduler Configuration](.github/CLOUD_SCHEDULER.md) - Scheduled execution setup
- [Secrets Configuration](.github/secrets.example) - Required GitHub secrets