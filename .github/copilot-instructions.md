# AI Coding Agent Instructions

## Operational Context
- Read `README.md` for complete project context, features, architecture, and configuration details.
- App: Python 3.x Flask service exposing `/execute` to orchestrate multiple HTTP calls.
- Key modules:
  - `src/app.py`: Flask app, `/execute`, execution (parallel/sequential, aggregation of results.
  - `src/config.py`: dotenv loading, parsing endpoint configuration, template substitution.
- Source layout: `src/` contains production code; `test/` and `integration/` contains tests.
- Virtual environment: `.venv` (managed by `envtool.sh`).

## Required Commands
Run repository workflows only through `envtool.sh`:
- `bash envtool.sh code-check`
- `bash envtool.sh test`
- `bash envtool.sh mutation-check` (only when requested)

## Endpoint Configuration
- Endpoints are provided via env var `ENDPOINTS` (JSON array) and/or request body.
- Before JSON parsing, `${VAR_NAME}` placeholders are substituted from environment variables.
  - Missing variables must raise clear English errors.
- Each endpoint supports:
  - URL string: `"https://example.com/api"`
  - Object:
    - `url` (required), `method` (default POST), `headers`, `params`, `json`/`body`, `timeout`

## Important Notes (Runtime Invariants)
- The application MUST be stateless and idempotent (safe for repeated/scheduled executions).
- Default execution is parallel (I/O-bound) using `ThreadPoolExecutor`.
- Sequential mode is available via `parallel: false`.
- Endpoint executions are independent: one failure MUST NOT stop the rest.
- Results are aggregated into a single response.
- Environment variables are loaded once at application start (via `load_dotenv()`).

## Execution Mode
- Default: parallel execution (I/O-bound HTTP) using `ThreadPoolExecutor`.
- Optional: sequential mode to preserve strict ordering.
- Response includes `execution_mode`.

## Language Policy (Strict)
- Human-visible conversation/output to the user: MUST be in Spanish.
- Repository content MUST be English-only: identifiers, comments, docstrings, documentation, logs, and exception/error messages.
- If non-English text is found in the repo, translate it to clear technical English without changing meaning.

## Engineering Principles
- DRY, SOLID, Clean Code.
- Minimal, safe diffs; avoid refactors unless required.
- Preserve stateless and idempotent behavior (safe for scheduled/repeated executions).
- Do not change functional behavior unless strictly required by the task.
- Do not add `print()` statements; this project uses proper logging.

## Configuration & Dependencies
- Centralize configuration; avoid hardcoded parameters.
- Use environment variables for credentials/secrets.
- Do not introduce undeclared dependencies; use only those already declared.
- Do not access protected members.

## Naming & Style
- PascalCase: classes
- snake_case: functions/methods/variables
- UPPER_SNAKE_CASE: constants
- Max line length: 100 characters.

## Docstrings
- Public modules, classes, and public functions/methods MUST have detailed English docstrings.
- Private/internal helpers may be brief or omit docstrings unless required by linting.

## Type Checking (mypy)
- `bash envtool.sh code-check` must pass with mypy reporting ZERO errors.
- Add/refine type hints and typing constructs as needed; keep changes minimal and consistent.

## Quality Gates (Must Pass)
### `bash envtool.sh code-check`
- Must finish successfully with zero warnings/errors.
- If pylint reports a score, it must be exactly 10.0.
- mypy: zero errors.
- trivy (if installed): no HIGH or CRITICAL findings.
- Only allow local inline pylint disables, each with a brief English justification.

### `bash envtool.sh test`
- Zero test failures/errors.
- Coverage for `src` must be exactly 100% (pytest-cov line coverage).
- Do not game coverage:
  - no meaningless tests
  - no blanket `# pragma: no cover` / global exclusions
- Tests must be deterministic:
  - no real network calls; mock external HTTP
  - mock environment variables as needed

### `bash envtool.sh mutation-check` (When Requested)
- ZERO surviving mutants.
- Prefer strengthening/adding tests to kill mutants; change production code only if strictly
  required.

## Assertions Policy
- Avoid direct `assert` when required by repository policy; raise `AssertionError` explicitly.

## Automation Behavior (Run-to-completion Tasks)
- Do not ask questions or request confirmation.
- Do not narrate progress, plans, or intermediate steps.
- Do not pause for approvals or mention version control (no commits/branches/VCS talk).
- Loop: run the relevant command -> apply the smallest safe fix -> rerun until clean.

## Version Control Policy
- NEVER run git commands (no add/commit/push/branch/checkout).
- Leave commits and VCS actions to the user.
