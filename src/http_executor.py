"""HTTP request executor module.

This module handles HTTP request execution with support for parallel and sequential modes.
Follows Single Responsibility Principle (SRP) - handles only HTTP execution logic.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed  # pylint: disable=E0611
from typing import Dict, List, Tuple

import requests

from src.models import EndpointConfig, ExecutionResult, ExecutionStatus

# Maximum seconds to spend on retry cycles, matching Cloud Scheduler's max attempt-deadline.
_RETRY_ATTEMPT_DEADLINE_SECONDS = 1800.0


class HTTPExecutor:
    """Executes HTTP requests to configured endpoints.
    Supports both parallel (ThreadPoolExecutor) and sequential execution modes.
    Follows Strategy Pattern for execution strategies.
    """

    def __init__(self, max_workers: int = 10):
        """
        Initialize HTTP executor.
        Args:
            max_workers: Maximum number of parallel workers for ThreadPoolExecutor
        """
        self.max_workers = max_workers

    def execute_request(
        self, endpoint_config: EndpointConfig, default_payload=None
    ) -> requests.Response:
        """
        Execute a single HTTP request.
        Args:
            endpoint_config: EndpointConfig with request parameters
            default_payload: Default payload if no body is specified
        Returns:
            requests.Response object
        """
        # Determine payload source: prefer json_data, then body, then default_payload
        if endpoint_config.json_data is not None:
            payload = endpoint_config.json_data
        elif endpoint_config.body is not None:
            payload = endpoint_config.body
        else:
            payload = default_payload
        # Assign to json or data based on payload type
        json_data = None
        data = None
        if isinstance(payload, dict):
            json_data = payload
        elif payload is not None:
            data = payload
        return requests.request(
            endpoint_config.method,
            endpoint_config.url,
            headers=endpoint_config.headers,
            params=endpoint_config.params,
            timeout=endpoint_config.timeout,
            json=json_data,
            data=data,
        )

    def execute_single_endpoint(
        self, endpoint_idx: int, endpoint_config_raw, default_payload=None
    ) -> Tuple[ExecutionStatus, ExecutionResult]:
        """
        Execute a single endpoint and return status and result.
        Args:
            endpoint_idx: Index of the endpoint in the list
            endpoint_config_raw: Raw endpoint configuration (string or dict)
            default_payload: Default payload for requests without body
        Returns:
            Tuple of (ExecutionStatus, ExecutionResult)
        """
        endpoint_name = None
        try:
            # Parse endpoint configuration
            endpoint_config = EndpointConfig.from_config(endpoint_config_raw)
            endpoint_name = endpoint_config.url
            print(f"Executing: {endpoint_name}")
            response = self.execute_request(endpoint_config, default_payload)
            # Create result from response
            result = ExecutionResult.from_response(endpoint_name, endpoint_config.method, response)
            print(f"Completed: {endpoint_name} - Status: {response.status_code}")
            return (result.status, result)
        except (requests.exceptions.RequestException, ValueError) as exc:
            error_msg = f"Error on {endpoint_name or f'endpoint_{endpoint_idx}'}: {str(exc)}"
            print(error_msg)
            error_result = ExecutionResult.from_error(
                endpoint_name or f"endpoint_{endpoint_idx}", str(exc)
            )
            return (ExecutionStatus.ERROR, error_result)

    def execute_parallel(
        self, endpoints: List, default_payload=None
    ) -> Tuple[List[ExecutionResult], List[ExecutionResult], List[ExecutionResult]]:
        """
        Execute endpoints in parallel using ThreadPoolExecutor.
        Args:
            endpoints: List of endpoint configurations
            default_payload: Default payload for endpoints without body
        Returns:
            Tuple of (successes, warnings, errors) as lists of ExecutionResult
        """
        results = []
        warnings = []
        errors = []
        print(f"🚀 Execution mode: PARALLEL (max_workers={self.max_workers})")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(self.execute_single_endpoint, idx, config, default_payload): idx
                for idx, config in enumerate(endpoints)
            }
            # Collect results as they complete
            for future in as_completed(future_to_idx):
                status, result = future.result()
                if status == ExecutionStatus.SUCCESS:
                    results.append(result)
                elif status == ExecutionStatus.WARNING:
                    warnings.append(result)
                else:  # ERROR
                    errors.append(result)
        return results, warnings, errors

    def execute_sequential(
        self, endpoints: List, default_payload=None
    ) -> Tuple[List[ExecutionResult], List[ExecutionResult], List[ExecutionResult]]:
        """
        Execute endpoints sequentially (one by one).
        Args:
            endpoints: List of endpoint configurations
            default_payload: Default payload for endpoints without body
        Returns:
            Tuple of (successes, warnings, errors) as lists of ExecutionResult
        """
        results = []
        warnings = []
        errors = []
        print("🔄 Execution mode: SEQUENTIAL")
        for endpoint_idx, endpoint_config in enumerate(endpoints):
            status, result = self.execute_single_endpoint(
                endpoint_idx, endpoint_config, default_payload
            )
            if status == ExecutionStatus.SUCCESS:
                results.append(result)
            elif status == ExecutionStatus.WARNING:
                warnings.append(result)
            else:  # ERROR
                errors.append(result)
        return results, warnings, errors

    def execute(
        self, endpoints: List, parallel: bool = True, default_payload=None
    ) -> Tuple[List[ExecutionResult], List[ExecutionResult], List[ExecutionResult]]:
        """
        Execute endpoints in parallel or sequential mode.
        Args:
            endpoints: List of endpoint configurations
            parallel: If True, execute in parallel; otherwise sequential
            default_payload: Default payload for endpoints without body
        Returns:
            Tuple of (successes, warnings, errors) as lists of ExecutionResult
        """
        # Use sequential mode for single endpoint or if parallel is disabled
        if not parallel or len(endpoints) <= 1:
            return self.execute_sequential(endpoints, default_payload)
        return self.execute_parallel(endpoints, default_payload)

    def _partition_errors_for_retry(
        self,
        errors: List[ExecutionResult],
        pending_configs: List,
    ) -> Tuple[List, List[ExecutionResult], List[ExecutionResult]]:
        """
        Partition failed results into retriable configs and permanent errors.

        Builds a URL → raw-config map from pending_configs so each failed
        ExecutionResult can be correlated back to its original configuration.
        Endpoints whose raw config is not a str/dict (raises ValueError in
        from_config) are silently skipped — they produce "endpoint_N" results
        that won't match any URL key and will become permanent errors.

        Args:
            errors: ERROR results from the latest execute() call
            pending_configs: Raw configs that were attempted in that call
        Returns:
            Tuple of (retriable_raw_configs, retriable_errors, permanent_errors)
        """
        retry_url_map: Dict[str, List] = {}
        for cfg in pending_configs:
            try:
                endpoint_config = EndpointConfig.from_config(cfg)
                retry_url_map.setdefault(endpoint_config.url, []).append(cfg)
            except ValueError:
                pass  # non-str/dict configs cannot be retried

        retriable_configs: List = []
        retriable_errors: List[ExecutionResult] = []
        permanent_errors: List[ExecutionResult] = []

        for error in errors:
            configs_for_url = retry_url_map.get(error.endpoint)
            if configs_for_url:
                retriable_configs.append(configs_for_url.pop(0))
                retriable_errors.append(error)
            else:
                permanent_errors.append(error)

        return retriable_configs, retriable_errors, permanent_errors

    def execute_with_retry(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        endpoints: List,
        parallel: bool = True,
        default_payload=None,
        max_attempts: int = 3,
        backoff_base_seconds: float = 2.0,
        backoff_max_seconds: float = 30.0,
    ) -> Tuple[List[ExecutionResult], List[ExecutionResult], List[ExecutionResult]]:
        """
        Execute endpoints with internal retry, limited only to endpoints that failed.

        Successful and warning endpoints are never re-executed. Only ERROR endpoints
        are retried up to max_attempts times total with exponential backoff between
        attempts. Retries stop early if the elapsed time would exceed the Cloud
        Scheduler attempt-deadline budget (_RETRY_ATTEMPT_DEADLINE_SECONDS).

        Args:
            endpoints: List of endpoint configurations (strings or dicts)
            parallel: If True, execute in parallel; otherwise sequential
            default_payload: Default payload for endpoints without body
            max_attempts: Maximum total attempts per endpoint (1 = no retry)
            backoff_base_seconds: Base for exponential backoff in seconds
            backoff_max_seconds: Maximum backoff cap in seconds
        Returns:
            Tuple of (successes, warnings, errors) as lists of ExecutionResult
        """
        start_time = time.monotonic()
        all_results: List[ExecutionResult] = []
        all_warnings: List[ExecutionResult] = []
        final_errors: List[ExecutionResult] = []
        pending_configs = list(endpoints)

        for attempt_num in range(1, max_attempts + 1):
            results, warnings, errors = self.execute(pending_configs, parallel, default_payload)

            # Stamp the attempt number on every result from this pass
            for result in results:
                result.attempts = attempt_num
            for warning in warnings:
                warning.attempts = attempt_num

            all_results.extend(results)
            all_warnings.extend(warnings)

            if not errors:
                break  # all endpoints succeeded or warned — nothing to retry

            retriable_configs, retriable_errors, permanent_errors = (
                self._partition_errors_for_retry(errors, pending_configs)
            )
            for error in permanent_errors:
                error.attempts = attempt_num
            final_errors.extend(permanent_errors)

            if not retriable_configs or attempt_num == max_attempts:
                for error in retriable_errors:
                    error.attempts = attempt_num
                final_errors.extend(retriable_errors)
                break

            # Exponential backoff: base * 2^(attempt-1), capped at max
            backoff = min(backoff_base_seconds * (2 ** (attempt_num - 1)), backoff_max_seconds)

            # Respect the Cloud Scheduler attempt-deadline budget
            elapsed = time.monotonic() - start_time
            if elapsed + backoff >= _RETRY_ATTEMPT_DEADLINE_SECONDS:
                print(
                    f"⏱ Retry budget exhausted after {elapsed:.1f}s — "
                    f"stopping with {len(retriable_errors)} unresolved error(s)"
                )
                for error in retriable_errors:
                    error.attempts = attempt_num
                final_errors.extend(retriable_errors)
                break

            print(
                f"🔁 Retrying {len(retriable_configs)} failed endpoint(s) "
                f"(attempt {attempt_num + 1}/{max_attempts}, backoff={backoff:.1f}s)"
            )
            time.sleep(backoff)
            pending_configs = retriable_configs

        return all_results, all_warnings, final_errors
