
# GCP Scheduler Runner

Python Flask project that executes multiple endpoints in sequence, orchestrated
by a main `/execute` endpoint.

## Features

- Main endpoint `/execute` that orchestrates multiple endpoints
- **Parallel execution** using `ThreadPoolExecutor` (default behavior, configurable)
- **Sequential execution** mode available for controlled workflows
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

## Usage

### Start the server

```bash
python app.py
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

**Response includes execution mode**:
```json
{
  "success": true,
  "total_endpoints": 3,
  "successful": 3,
  "failed": 0,
  "execution_mode": "parallel",
  "results": [...],
  "errors": []
}
```

**Notes**:
- Parallel execution is ideal for I/O-bound HTTP requests
- Order of execution is not guaranteed in parallel mode
- Single endpoint requests automatically use sequential mode
- Error handling works the same in both modes

### Health Check

```bash
curl http://localhost:3000/health
```

## Tests

Run the project's tests with coverage using the helper script:

```bash
bash envtool.sh test
```

Or run manually:

```bash
source .venv/bin/activate
pytest test_app.py -v --cov=app --cov=config --cov-report=term-missing
```

### Test Coverage

The project aims for full coverage of the core logic. Tests cover:
- All endpoints (/, /health, /task1, /task2, /task3, /execute)
- Request execution functions
- Validation and configuration parsing
- Error handling and exceptional cases

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

- Formatting: Black + isort
- Linting: Pylint + autoflake
- Tests: pytest with coverage

Run quality checks with:

```bash
bash envtool.sh code-check
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
# Example: Execute every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
gcloud scheduler jobs create http gcp-scheduler-runner-job \
  --location=us-central1 \
  --schedule="0 */6 * * *" \
  --uri="https://YOUR-SERVICE-URL.run.app/execute" \
  --http-method=POST \
  --headers="X-API-Key=YOUR_API_KEY_HERE" \
  --attempt-deadline=300s
```

**Timezone Conversion Examples**:
- 9:00 AM EST (UTC-5) → `--schedule="0 14 * * *"` (14:00 UTC)
- 9:00 AM PST (UTC-8) → `--schedule="0 17 * * *"` (17:00 UTC)
- 6:00 PM EST → `--schedule="0 23 * * *"` (23:00 UTC same day)

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