"""HTTP request executor module.

This module handles HTTP request execution with support for parallel and sequential modes.
Follows Single Responsibility Principle (SRP) - handles only HTTP execution logic.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed  # pylint: disable=E0611
from typing import List, Tuple

import requests

from src.models import EndpointConfig, ExecutionResult, ExecutionStatus


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
