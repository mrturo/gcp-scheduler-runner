# AI Coding Agent Instructions

## Project Overview
Python 3.x Flask application for Google Cloud Run that orchestrates the execution of multiple HTTP endpoints in sequence through a main `/execute` endpoint. Designed to be triggered by GCP Cloud Scheduler to automate multi-step workflows with flexible endpoint configurations supporting cURL-like syntax.

## Tech Stack

- **Framework**: Flask 3.0.0
- **HTTP Client**: requests 2.31.0
- **Configuration**: python-dotenv 1.0.0
- **Python Version**: 3.x

## Architecture & Data Flow

### Core Flow (See [app.py](app.py))
1. **Entry**: `GET/POST /execute` endpoint → `execute_endpoints()`
2. **Load**: Retrieve endpoint configurations from environment (`ENDPOINTS`) or request body
3. **Resolve**: Template variables in `ENDPOINTS` using `${VAR_NAME}` syntax (see [config.py](config.py))
4. **Parse**: Support simple URLs or full cURL-like configurations
5. **Execute**: Parallel execution (default) or sequential execution with timeout and error handling
   - Parallel mode uses `ThreadPoolExecutor` with configurable `max_workers`
   - Sequential mode preserves original behavior for controlled workflows
6. **Aggregate**: Collect results from all executions (success/failure) using `as_completed()`
7. **Return**: JSON response with execution details, timestamps, errors, and `execution_mode`

### Module Structure
- **[app.py](app.py)**: Flask app, endpoints, request execution logic, parallel/sequential execution
- **[config.py](config.py)**: Environment variable loading and endpoint configuration parsing
- **[envtool.sh](envtool.sh)**: Bash script for environment and deployment management
- **Tests**: `test_app.py`, `test_endpoints.py`

## Code Style & Principles

### Core Principles
- Apply **DRY, SOLID, Clean Code** principles throughout
- Implement design patterns when appropriate (Factory, Strategy, Adapter, etc.)
- Keep code modular, scalable, secure, and efficient
- Code must be **idempotent and safe for repeated/scheduled executions**
- Prioritize computational and memory efficiency

### Configuration & Dependencies
- Centralize configuration, avoid hardcoded parameters
- Use environment variables for credentials and sensitive configurations
- Dependencies only from [requirements.txt](requirements.txt) or [requirements-dev.txt](requirements-dev.txt)
- Never access protected members or use undeclared dependencies

### Naming Conventions
- `PascalCase` for classes
- `snake_case` for functions, methods, variables
- `UPPER_SNAKE_CASE` for constants
- Underscore prefix for private helpers (e.g., `_execute_single_endpoint`)
- **All code objects, comments, docstrings in English** (no Spanish in code)

### Language Policy
- **Code**: All code, comments, docstrings, and technical documentation MUST be written in English
- **Chat Interactions**: All conversations through GitHub Copilot extension and Copilot CLI MUST be in Spanish
- This applies to responses, explanations, questions, and any conversational output
- Technical terms in conversations can remain in English when appropriate (e.g., "Flask", "endpoint", "timeout")

### Code Quality
- **Line length**: 100 chars max (not 88/79)
- **Docstrings**: Use triple-quoted docstrings for all public functions/classes with detailed descriptions
- **Type Hints**: Not currently used; maintain consistency with existing code
- **Error Handling**: Use try-except blocks with descriptive error messages in English
- **Avoid**: Direct `assert` (raise `AssertionError`), hardcoded configs
- **Testing**: Maintain high test coverage with pytest
- Code must be directly executable, complete, and functional

### Communication Style
- Professional, technical, and direct; no embellishments
- Challenge assumptions to foster learning
- Request clarifications only when necessary for accuracy
- In step-by-step processes, deliver one step per message and wait for confirmation

## Critical Patterns

### 1. Endpoint Configuration Format
Each endpoint can be one of the following:
- **Simple URL string**: `"http://example.com/api"`
- **Full cURL-like configuration object**:
  - `url`: endpoint URL (required)
  - `method`: HTTP method - GET, POST, PUT, DELETE, PATCH (default: POST)
  - `headers`: dictionary of headers
  - `json`/`body`: request payload (JSON dict or raw string)
  - `params`: query parameters
  - `timeout`: timeout in seconds (default: 30)

**Validation Rules**:
- URLs must be valid HTTP/HTTPS
- Method must be one of the supported HTTP methods
- Timeout must be reasonable (> 0, typically ≤ 300 seconds)
- Headers must be valid dictionary format

### 2. Request Execution Logic
Defined in [execute_request](app.py) function:
- Supports both simple URL strings and full configuration objects
- Uses `requests.request()` for flexibility with all HTTP methods
- Automatic fallback to `default_payload` when no body is specified
- Distinguishes between JSON payloads (`json=`) and raw data (`data=`)
- Always includes timeout to prevent hanging requests
- Returns response object for status code and content inspection

### 3. Configuration Loading & Template Variables
All configuration loading uses [config.py](config.py):
- `load_dotenv()` executed once at module import
- Reads `ENDPOINTS` environment variable (JSON array)
- **Template variable substitution**: Replaces `${VAR_NAME}` with environment values before parsing JSON
  - Separates sensitive credentials from endpoint structure
  - Allows `ENDPOINTS` structure to be safely committed to version control
  - Raises clear error if referenced variable is undefined
- Falls back to individual `ENDPOINT_1`, `ENDPOINT_2`, etc.
- Supports both JSON parsing and raw string URLs
- Clear error messages in English when validation fails

**Template Variable Examples**:
```bash
# .env file
ENDPOINT_API_KEY=secret_token_xyz
ENDPOINTS='[{"url": "https://api.example.com", "headers": {"Authorization": "Bearer ${ENDPOINT_API_KEY}"}}]'
```

At runtime, `${ENDPOINT_API_KEY}` is replaced with `secret_token_xyz` before JSON parsing.

### 4. Parallel Execution Strategy
The `/execute` endpoint supports both parallel and sequential execution modes:

**Parallel Mode (Default)**:
- Uses `concurrent.futures.ThreadPoolExecutor` for I/O-bound HTTP requests
- Configurable via `parallel` parameter (default: `true`)
- Configurable `max_workers` (default: `min(10, num_endpoints)`)
- Submits all endpoint tasks to thread pool using `executor.submit()`
- Collects results as they complete using `as_completed()`
- Ideal for reducing total execution time with independent endpoints

**Sequential Mode**:
- Enabled by setting `parallel: false` in request body
- Preserves original behavior for controlled workflows
- Maintains strict execution order
- Automatically used for single-endpoint requests

**Implementation Details**:
- Helper function `_execute_single_endpoint()` designed for both modes
- Returns tuple: `(success: bool, result_or_error: dict)`
- Error handling works identically in both modes
- Response includes `execution_mode` field: `"parallel"` or `"sequential"`

## Development Workflow

### Version Control Policy

**CRITICAL: NO AUTOMATIC GIT COMMITS**
- **NEVER** execute `git commit`, `git add`, `git push`, or any git command that modifies version control state
- **NEVER** use tools like `run_in_terminal` to execute git commands
- **NEVER** create or modify git-related files (e.g., `.gitignore` updates that require commits)
- The user MUST review all changes and commit them manually
- Only create, modify, or delete files as requested - let the user handle version control
- If the user asks about git or commits, remind them they need to commit manually

**Rationale**: The user needs full control over what goes into version control and when. All file changes should be visible in the working directory for the user to review, test, and commit at their discretion.

### Environment Setup ([envtool.sh](envtool.sh))
```bash
bash envtool.sh install [dev|prod]    # Create .venv + install dependencies (requires Python 3.8+)
bash envtool.sh reinstall [dev|prod]  # Clean all + fresh install (dev includes linters/formatters)
bash envtool.sh uninstall             # Remove .venv and all cache/artifacts
bash envtool.sh clean-env             # Remove only .venv directory
bash envtool.sh clean-cache           # Remove __pycache__, .pytest_cache, etc.
                                      # ALWAYS verify no errors or warnings remain after execution and fix them
bash envtool.sh code-check            # Run black, isort, autoflake, pylint
bash envtool.sh status                # Check environment status (Python version, pip, files)
bash envtool.sh test                  # Run pytest with coverage report
                                      # ALWAYS verify no errors or warnings remain after execution and fix them
                                      # ALWAYS ensure 100% coverage - fix any gaps immediately
bash envtool.sh start                 # Start Flask server (auto-loads .env, frees port if busy)
bash envtool.sh execute               # Execute configured endpoints (from ENDPOINTS env var)
```

**Environment Variables** (`.env` file):
```env
PORT=5000                           # Flask server port
ENDPOINTS='[...]'                   # JSON array of endpoint configurations
ENDPOINT_1='http://...'            # Individual endpoints (alternative)
# Add any custom headers or auth tokens as needed
```

##Coverage Requirement**: ALWAYS maintain 100% test coverage. After running tests, verify coverage reaches 100% and add missing tests immediately if gaps are found.

**# Testing Patterns (High coverage expected)

**Mocking Strategy** ([test_app.py](test_app.py), [test_endpoints.py](test_endpoints.py)):
1. Always mock external HTTP calls using `unittest.mock` or `pytest-mock`
2. Mock `requests.request()` to return controlled response objects
3. Mock environment variables using `monkeypatch` fixture or `os.environ` patching
4. Create fake response objects with `.status_code`, `.text`, `.json()` attributes

**Test Structure**:
- Separate files for different test concerns (`test_app.py`, `test_endpoints.py`)
- Test both success and failure scenarios
- Test edge cases: empty endpoints, invalid configurations, timeouts, errors
- Validate both simple URL strings and full configuration objects

**Example Mock Pattern**:
```python
def test_execute_request(monkeypatch):
    class MockResponse:
        status_code = 200
        text = '{"result": "success"}'
    
    def mock_request(*args, **kwargs):
        return MockResponse()
    
    monkeypatch.setattr('requests.request', mock_request)
    # Test code here
```

## Cloud Deployment

**Target Platform**: Google Cloud Platform (GCP) - Cloud Run
**Trigger Mechanism**: GCP Cloud Scheduler (HTTP trigger)

**Build & Deploy**:
```bash
# Build Docker image (if using containerized deployment)
docker build -t gcr.io/<PROJECT_ID>/gcp-scheduler-runner .

# Deploy to Cloud Run (example configuration)
gcloud run deploy gcp-scheduler-runner \
  --image gcr.io/<PROJECT_ID>/gcp-scheduler-runner \
  --region=<REGION> \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=1 \
  --timeout=300s \
  --set-env-vars="ENDPOINTS=[...]"
```

**Configuration**:
- Environment variables via `.env` file (local) or GCP environment configuration (production)
- Port configurable via `PORT` environment variable
- Secrets should use GCP Secret Manager (not hardcoded)

## Common Tasks

**Add new endpoint to configuration**:
1. Add to `ENDPOINTS` array in `.env` file (JSON format)
2. Or add individual `ENDPOINT_N` variable
3. Test with `/execute` endpoint

**Modify request execution logic**:
- Edit [execute_request](app.py) function
- Update timeout handling, error handling, or response processing
- Add tests in [test_app.py](test_app.py)

**Change response format**:
- Modify return statements in [app.py](app.py) endpoints
- Ensure `jsonify()` is used for all JSON responses
- Include `timestamp` in ISO format: `datetime.now().isoformat()`

**Debug endpoint execution**:
```bash
# Run Flask server locally
python app.py

# Test execute endpoint
curl -X POST http://localhost:5000/execute

# With custom endpoints
curl -X POST http://localhost:5000/execute \
  -H "Content-Type: application/json" \
  -d '{"endpoints": ["http://example.com/api"]}'
```

## Important Notes

- This application is designed to be **stateless** and **idempotent**
- Endpoints are executed **in parallel by default** (configurable to sequential for controlled workflow)
- Parallel execution uses `ThreadPoolExecutor` for I/O-bound HTTP requests
- Sequential mode available via `parallel: false` parameter
- Each endpoint execution is independent; one failure doesn't stop the rest
- Results are aggregated and returned in a single response
- Environment variables are loaded once at application start via `load_dotenv()`
- Safe for repeated/scheduled executions (GCP Cloud Scheduler compatible)

## Key Files Reference
- [README.md](README.md): Full feature docs, usage examples, endpoint configuration
- [app.py](app.py): Main Flask application with all endpoints
- [config.py](config.py): Configuration utilities and environment variable parsing
- [envtool.sh](envtool.sh): Development and deployment scripts
- [requirements.txt](requirements.txt): Production dependencies
- [requirements-dev.txt](requirements-dev.txt): Development dependencies (testing, linting)
