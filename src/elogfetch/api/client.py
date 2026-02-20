"""HTTP client with Kerberos authentication for SLAC elog API."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any, TypeVar

import httpx
import stamina
from krtc import KerberosTicket
from pydantic import BaseModel

from ..exceptions import AuthenticationError
from ..utils import get_logger
from .gen.endpoint import Endpoint
from .gen.endpoint_models import (
    ELOG,
    EXPERIMENT_INFO,
    EXPERIMENT_NAMES_UPDATED_WITHIN,
    FILES,
    RUN,
    RUNS,
    WORKFLOW_DEFS,
)
from .gen.models import (
    ElogResponse,
    ExperimentNamesUpdatedWithinResponse,
    FilesResponse,
    InfoResponse,
    RunsResponse,
    SingleRunResponse,
    WorkflowDefinitionsResponse,
)

logger = get_logger()

# Default values (can be overridden via Config)
DEFAULT_BASE_URL = "https://pswww.slac.stanford.edu"
DEFAULT_KERBEROS_PRINCIPAL = "HTTP@pswww.slac.stanford.edu"

# Retry configuration
REQUEST_TIMEOUT = 30

M = TypeVar("M", bound=BaseModel)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class ElogClient:
    """Async HTTP client for SLAC elog API with Kerberos authentication."""

    def __init__(
        self,
        base_url: str | None = None,
        kerberos_principal: str | None = None,
    ):
        """Initialize the client.

        Args:
            base_url: Base URL for the elog API (default: SLAC pswww)
            kerberos_principal: Kerberos principal for authentication
        """
        self.base_url = base_url or DEFAULT_BASE_URL
        self.kerberos_principal = kerberos_principal or DEFAULT_KERBEROS_PRINCIPAL
        self._auth_headers: dict[str, str] | None = None
        self._session = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        self._sync_session = httpx.Client(timeout=REQUEST_TIMEOUT)

    async def __aenter__(self) -> ElogClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._session.aclose()

    def _check_kerberos_auth_sync(self) -> bool:
        """Check if Kerberos authentication is valid (blocking)."""
        try:
            result = subprocess.run(
                ["klist", "-s"],
                capture_output=True,
                check=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get Kerberos authentication headers.

        Returns:
            Dictionary of HTTP headers with Kerberos authentication

        Raises:
            AuthenticationError: If Kerberos ticket is not available
        """
        if self._auth_headers is not None:
            return self._auth_headers

        valid = await asyncio.to_thread(self._check_kerberos_auth_sync)
        if not valid:
            raise AuthenticationError(
                "Kerberos authentication not found or expired. "
                "Please run 'kinit' to authenticate."
            )

        try:
            self._auth_headers = await asyncio.to_thread(
                lambda: KerberosTicket(self.kerberos_principal).getAuthHeaders()
            )
            return self._auth_headers
        except Exception as e:
            raise AuthenticationError(f"Failed to get Kerberos ticket: {e}") from e

    @stamina.retry(on=_is_retryable)
    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        """Make a GET request to the API.

        Transient errors (5xx, network) are retried automatically via stamina.

        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            require_auth: Whether to use Kerberos authentication

        Returns:
            JSON response from the API

        Raises:
            APIError: If the request fails with a non-retryable error
            AuthenticationError: If authentication fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = await self._get_auth_headers() if require_auth else {}
        response = await self._session.get(url, headers=headers, params=params)

        # On 401, refresh the Kerberos ticket and retry once
        if response.status_code == 401 and require_auth:
            logger.debug(f"Got 401 for {endpoint}, refreshing auth headers")
            self._auth_headers = None
            headers = await self._get_auth_headers()
            response = await self._session.get(url, headers=headers, params=params)
            if response.status_code == 401:
                raise AuthenticationError(
                    f"Access denied for {endpoint}. Check if you have permission."
                )

        if response.status_code == 403:
            raise AuthenticationError(
                f"Access denied to {endpoint}. You may not have permission."
            )

        response.raise_for_status()
        return response.json()

    async def fetch(
        self,
        endpoint: Endpoint[M],
        params: dict[str, Any] | None = None,
        **path_params: Any,
    ) -> M:
        """Fetch and validate a typed API endpoint.

        Args:
            endpoint: Typed endpoint descriptor
            params: Query parameters
            **path_params: URL path parameters (e.g. experiment_name="mfxc00118")

        Returns:
            Validated Pydantic model instance
        """
        url = endpoint.url(**path_params)
        data = await self.get(url, params=params, require_auth=endpoint.require_auth)
        return endpoint.model.model_validate(data)

    async def get_files(self, experiment_id: str) -> FilesResponse:
        return await self.fetch(FILES, experiment_name=experiment_id)

    async def get_experiments(
        self, offset_secs: int
    ) -> ExperimentNamesUpdatedWithinResponse:
        return await self.fetch(
            EXPERIMENT_NAMES_UPDATED_WITHIN, params={"offset_secs": offset_secs}
        )

    async def get_experiment_info(self, experiment_id: str) -> InfoResponse:
        return await self.fetch(EXPERIMENT_INFO, experiment_name=experiment_id)

    async def get_elog(self, experiment_id: str) -> ElogResponse:
        return await self.fetch(ELOG, experiment_name=experiment_id)

    async def get_runs(self, experiment_id: str) -> RunsResponse:
        return await self.fetch(RUNS, experiment_name=experiment_id)

    async def get_run(
        self, experiment_id: str, run_num: int | str
    ) -> SingleRunResponse:
        return await self.fetch(RUN, experiment_name=experiment_id, run_num=run_num)

    async def get_workflows(self, experiment_id: str) -> WorkflowDefinitionsResponse:
        return await self.fetch(WORKFLOW_DEFS, experiment_name=experiment_id)
