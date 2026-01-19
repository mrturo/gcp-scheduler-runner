#!/bin/bash

# Color definitions for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function start_project() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev${NC}"
        exit 1
    fi
    echo -e "${GREEN}🚀 Starting the Flask server...${NC}"
    source .venv/bin/activate
    # Load variables from .env if it exists
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
    export PORT="${PORT:-3000}"

    # Force free the port before starting
    if lsof -ti :$PORT >/dev/null 2>&1; then
        echo -e "${RED}⚠️  Port $PORT is in use. Killing process...${NC}"
        lsof -ti :$PORT | xargs kill -9 || true
    fi

    python src/app.py
    deactivate
}

function run_tests() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev${NC}"
        exit 1
    fi
    echo -e "${GREEN}🧪 Running tests...${NC}"
    source .venv/bin/activate
    pytest test/ -v --cov=src --cov-report=term-missing
    local status=$?
    deactivate
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed successfully.${NC}"
    else
        echo -e "${RED}❌ Some tests failed. Check the log above.${NC}"
        exit $status
    fi
}

function clean_cache() {
    echo -e "${GREEN}🧹 Cleaning project cache and artifacts...${NC}"
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .mypy_cache .cache dist build *.egg-info htmlcov .coverage
    echo -e "${GREEN}✅ Cache and artifacts removed.${NC}"
}

function clean_env() {
    if [ -d ".venv" ]; then
        echo -e "${GREEN}🪨 Removing virtual environment (.venv)...${NC}"
        rm -rf .venv
        echo -e "${GREEN}✅ .venv successfully removed.${NC}"
    else
        echo -e "${GREEN}ℹ️  .venv directory not found. Nothing to remove.${NC}"
    fi
}

function clean_all() {
    clean_cache
    clean_env
}

function code_check() {
    set -e
    local ci_mode=false
    local exit_code=0
    
    # Check if --ci flag is present
    if [[ "$1" == "--ci" ]]; then
        ci_mode=true
        echo -e "${YELLOW}🔒 Running in CI mode (check-only, no modifications)${NC}"
    fi
    
    local paths=("src" "test")
    echo -e "${GREEN}📁 Checking code in: ${paths[*]}${NC}"
    # If a virtualenv exists, activate it so linters can resolve dependencies
    if [ -f ".venv/bin/activate" ]; then
        echo -e "${GREEN}🔌 Activating .venv for code checks...${NC}"
        source .venv/bin/activate
    fi
    
    # Only run if the tools are installed, else warn if missing
    if command -v black >/dev/null 2>&1; then
        echo -e "${GREEN}🎨 Running black...${NC}"
        if [ "$ci_mode" = true ]; then
            black --check src/*.py test/*.py
        else
            black src/*.py test/*.py
        fi
    else
        echo -e "${YELLOW}⚠️  black not found, skipping...${NC}"
    fi

    if command -v isort >/dev/null 2>&1; then
        echo -e "${GREEN}🔧 Running isort...${NC}"
        if [ "$ci_mode" = true ]; then
            isort --check-only src/*.py test/*.py
        else
            isort src/*.py test/*.py
        fi
    else
        echo -e "${YELLOW}⚠️  isort not found, skipping...${NC}"
    fi

    if command -v autoflake >/dev/null 2>&1; then
        echo -e "${GREEN}🧹 Running autoflake...${NC}"
        if [ "$ci_mode" = true ]; then
            autoflake --remove-all-unused-imports --remove-unused-variables --check --recursive src/*.py test/*.py
        else
            autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive src/*.py test/*.py
        fi
    else
        echo -e "${YELLOW}⚠️  autoflake not found, skipping...${NC}"
    fi

    if [ -f ".venv/bin/pylint" ]; then
        echo -e "${GREEN}🔍 Running pylint on all Python files in src/ and test/...${NC}"
        PY_FILES=$(find src test -type f -name "*.py")
        if [ -n "$PY_FILES" ]; then
            # Fail if score < 10.0 (any recommendation), and do not continue on any warning
            PYTHONPATH=src .venv/bin/pylint --persistent=no --fail-under=10.0 $PY_FILES
        else
            echo -e "${YELLOW}⚠️  No Python files found in src/ or test/, skipping pylint...${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  pylint not found, skipping...${NC}"
    fi

    if command -v mypy >/dev/null 2>&1; then
        echo -e "${GREEN}🔬 Running mypy type checker...${NC}"
        PYTHONPATH=src mypy src test --ignore-missing-imports
    else
        echo -e "${YELLOW}⚠️  mypy not found, skipping...${NC}"
    fi

    if command -v trivy >/dev/null 2>&1; then
        echo -e "${GREEN}🔒 Running trivy security scanner...${NC}"
        trivy fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --skip-files '.env' .
    else
        echo -e "${YELLOW}⚠️  trivy not found, skipping...${NC}"
    fi
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Quality Checks Completed${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

function check_status() {
    echo -e "${GREEN}🔎 Checking environment status...${NC}"
    if [ -d ".venv" ]; then
        echo -e "${GREEN}✔️  The virtual environment (.venv) exists.${NC}"
    else
        echo -e "${RED}❌ The virtual environment (.venv) is missing.${NC}"
    fi
    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}✔️  requirements.txt found.${NC}"
    else
        echo -e "${RED}❌ requirements.txt is missing.${NC}"
    fi
    if [ -x ".venv/bin/python" ]; then
        VENV_PYTHON_VERSION=$(./.venv/bin/python --version 2>&1)
        VENV_PIP_VERSION=$(./.venv/bin/pip --version 2>&1)
        echo -e "${GREEN}🐍 Python in .venv: ${VENV_PYTHON_VERSION}${NC}"
        echo -e "${GREEN}📦 Pip in .venv: ${VENV_PIP_VERSION}${NC}"
    fi
    echo -e "${GREEN}🔚 Status check finished.${NC}"
}

function install() {
    local mode="${1:-dev}"
    local PYTHON_BINARY="${PYTHON_BINARY_OVERRIDE:-python3}"
    local REQUIRED_MAJOR=3
    local REQUIRED_MINOR=8

    if [[ "$mode" != "prod" && "$mode" != "dev" ]]; then
        echo -e "${RED}❌ You must specify the installation mode: 'prod' or 'dev'.${NC}"
        echo -e "${RED}   Example: bash envtool.sh install prod${NC}"
        echo -e "${RED}   Example: bash envtool.sh install dev${NC}"
        exit 1
    fi

    echo -e "${GREEN}🚀 Installing Python environment with $PYTHON_BINARY...${NC}"
    find . -name '__pycache__' -exec rm -rf {} +

    PY_VERSION=$($PYTHON_BINARY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt "$REQUIRED_MAJOR" ] || { [ "$PY_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PY_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
        echo -e "${RED}❌ Python >= $REQUIRED_MAJOR.$REQUIRED_MINOR required. Found: $PY_VERSION${NC}"
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        echo -e "${GREEN}📦 Creating virtual environment (.venv) using $PYTHON_BINARY...${NC}"
        $PYTHON_BINARY -m venv .venv
    else
        echo -e "${GREEN}📁 Virtual environment already exists. Skipping creation.${NC}"
    fi

    echo -e "${GREEN}💡 Activating virtual environment...${NC}"
    source .venv/bin/activate

    echo -e "${GREEN}⬆️  Upgrading pip...${NC}"
    pip install --upgrade pip

    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}📄 Installing dependencies from requirements.txt...${NC}"
        pip install -r requirements.txt
    else
        echo -e "${RED}❌ requirements.txt not found. Please add one.${NC}"
        exit 1
    fi

    if [ "$mode" = "dev" ] && [ -f "requirements-dev.txt" ]; then
        echo -e "${GREEN}📄 Installing dev dependencies from requirements-dev.txt...${NC}"
        pip install -r requirements-dev.txt
    fi

    echo -e "${GREEN}✅ Environment ready. Activate with: source .venv/bin/activate${NC}"
}

function execute_logic() {
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ The virtual environment (.venv) does not exist. Run first: bash envtool.sh install dev${NC}"
        exit 1
    fi
    echo -e "${GREEN}🔄 Executing endpoint logic...${NC}"
    source .venv/bin/activate
    
    # Load variables from .env if it exists
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
    
    # Execute the logic using Python directly
    python << 'PYTHON_SCRIPT'
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import load_endpoints_from_env
from datetime import datetime
import requests
import json

def execute_request(endpoint_config, default_payload=None):
    """Execute an HTTP request based on the endpoint configuration."""
    # Support simple URL string or full configuration
    if isinstance(endpoint_config, str):
        endpoint_config = {"url": endpoint_config, "method": "POST"}

    endpoint_url = endpoint_config.get("url")
    http_method = endpoint_config.get("method", "POST").upper()
    headers = endpoint_config.get("headers", {})
    body = endpoint_config.get("body") or endpoint_config.get("json")
    params = endpoint_config.get("params", {})
    timeout = endpoint_config.get("timeout", 30)

    # If no body is defined, use the default payload
    if body is None and default_payload:
        body = default_payload

    # Prepare kwargs for requests
    request_kwargs = {"timeout": timeout, "headers": headers, "params": params}

    # Add body according to its type
    if body is not None:
        if isinstance(body, dict):
            request_kwargs["json"] = body
        else:
            request_kwargs["data"] = body

    # Execute the request
    response = requests.request(http_method, endpoint_url, **request_kwargs)
    return response

def main():
    results = []
    errors = []

    try:
        endpoints = load_endpoints_from_env()
    except ValueError as e:
        print(f"\n⚠️  Error loading endpoints: {e}")
        print("\n📊 Execution Results:")
        print(json.dumps({
            "success": False,
            "total_endpoints": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "errors": [{"error": str(e), "timestamp": datetime.now().isoformat()}]
        }, indent=2))
        return

    print(f"\n🎯 Found {len(endpoints)} endpoint(s) to execute\n")

    for endpoint_idx, endpoint_config in enumerate(endpoints):
        endpoint_name = None
        try:
            if isinstance(endpoint_config, str):
                endpoint_name = endpoint_config
            else:
                endpoint_name = endpoint_config.get("url", f"endpoint_{endpoint_idx}")

            print(f"⏳ Executing: {endpoint_name}")
            response = execute_request(endpoint_config, None)

            # Try to parse the response
            try:
                response_data = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                response_data = response.text

            results.append({
                "endpoint": endpoint_name,
                "method": (
                    endpoint_config.get("method", "POST")
                    if isinstance(endpoint_config, dict)
                    else "POST"
                ),
                "status_code": response.status_code,
                "response": response_data,
                "timestamp": datetime.now().isoformat(),
            })

            print(f"✅ Completed: {endpoint_name} - Status: {response.status_code}")

        except (requests.exceptions.RequestException, ValueError) as exc:
            error_msg = f"❌ Error on {endpoint_name or f'endpoint_{endpoint_idx}'}: {str(exc)}"
            print(error_msg)
            errors.append({
                "endpoint": endpoint_name or f"endpoint_{endpoint_idx}",
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            })

    print("\n" + "="*60)
    print("📊 Execution Results:")
    print("="*60)
    print(json.dumps({
        "success": len(errors) == 0,
        "total_endpoints": len(endpoints),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }, indent=2))

if __name__ == "__main__":
    main()
PYTHON_SCRIPT
    
    deactivate
    echo -e "${GREEN}✅ Execution completed.${NC}"
}

unset_proxies() {
    unset HTTP_PROXY
    unset HTTPS_PROXY
    unset http_proxy
    unset https_proxy
}

case "${1:-}" in
    install)
        unset_proxies
        shift
        install "$@"
        ;;
    reinstall)
        unset_proxies
        clean_all
        shift
        install "$@"
        ;;
    uninstall)
        unset_proxies
        clean_all
        ;;
    clean-env)
        unset_proxies
        clean_env
        ;;
    clean-cache)
        unset_proxies
        clean_cache
        ;;
    code-check)
        unset_proxies
        shift
        code_check "$@"
        ;;
    status)
        unset_proxies
        check_status
        ;;
    test)
        unset_proxies
        run_tests
        ;;
    start)
        unset_proxies
        start_project
        ;;
    execute)
        unset_proxies
        execute_logic
        ;;
    *)
        echo -e "${RED}Unsupported command. Use:${NC}"
        echo -e "${GREEN}  install [dev|prod]       ${NC}- Install dependencies"
        echo -e "${GREEN}  reinstall [dev|prod]     ${NC}- Clean and reinstall"
        echo -e "${GREEN}  uninstall                ${NC}- Remove virtual environment"
        echo -e "${GREEN}  clean-env                ${NC}- Remove .venv only"
        echo -e "${GREEN}  clean-cache              ${NC}- Clean Python cache files"
        echo -e "${GREEN}  code-check [--ci]        ${NC}- Run code quality checks (use --ci for check-only mode)"
        echo -e "${GREEN}  status                   ${NC}- Check environment status"
        echo -e "${GREEN}  test                     ${NC}- Run test suite"
        echo -e "${GREEN}  start                    ${NC}- Start Flask server"
        echo -e "${GREEN}  execute                  ${NC}- Execute configured endpoints"
        exit 1
        ;;
esac
