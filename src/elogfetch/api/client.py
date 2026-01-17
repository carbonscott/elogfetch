"""HTTP client with Kerberos authentication for SLAC elog API."""

from __future__ import annotations

import subprocess
from typing import Any

import requests
from krtc import KerberosTicket

from ..exceptions import APIError, AuthenticationError
from ..utils import get_logger

logger = get_logger()

# Default values (can be overridden via Config)
DEFAULT_BASE_URL = "https://pswww.slac.stanford.edu"
DEFAULT_KERBEROS_PRINCIPAL = "HTTP@pswww.slac.stanford.edu"


class ElogClient:
    """HTTP client for SLAC elog API with Kerberos authentication."""

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
        self._session = requests.Session()

    def _check_kerberos_auth(self) -> bool:
        """Check if Kerberos authentication is valid."""
        try:
            result = subprocess.run(
                ["klist", "-s"],
                capture_output=True,
                check=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_auth_headers(self) -> dict[str, str]:
        """Get Kerberos authentication headers.

        Returns:
            Dictionary of HTTP headers with Kerberos authentication

        Raises:
            AuthenticationError: If Kerberos ticket is not available
        """
        if self._auth_headers is not None:
            return self._auth_headers

        if not self._check_kerberos_auth():
            raise AuthenticationError(
                "Kerberos authentication not found or expired. "
                "Please run 'kinit' to authenticate."
            )

        try:
            self._auth_headers = KerberosTicket(self.kerberos_principal).getAuthHeaders()
            return self._auth_headers
        except Exception as e:
            raise AuthenticationError(f"Failed to get Kerberos ticket: {e}")

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            require_auth: Whether to use Kerberos authentication

        Returns:
            JSON response from the API

        Raises:
            APIError: If the request fails
            AuthenticationError: If authentication fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers() if require_auth else {}

        try:
            response = self._session.get(url, headers=headers, params=params)

            # On 401, try refreshing the Kerberos ticket once
            if response.status_code == 401 and require_auth:
                logger.debug(f"Got 401 for {endpoint}, refreshing auth headers")
                self._auth_headers = None  # Clear cached headers
                headers = self._get_auth_headers()  # Get fresh headers
                response = self._session.get(url, headers=headers, params=params)

                if response.status_code == 401:
                    raise AuthenticationError(
                        f"Access denied for {endpoint}. Check if you have permission."
                    )

            if response.status_code == 403:
                raise AuthenticationError(
                    f"Access denied to {endpoint}. You may not have permission."
                )

            if not response.ok:
                raise APIError(
                    f"API request failed: {response.status_code}",
                    status_code=response.status_code,
                    response=response.text[:500],
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            raise APIError(f"Network error: {e}")

    def get_public(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an unauthenticated GET request.

        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters

        Returns:
            JSON response from the API
        """
        return self.get(endpoint, params=params, require_auth=False)
