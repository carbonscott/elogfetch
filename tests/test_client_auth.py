import subprocess
from unittest.mock import patch

import pytest
from gssapi.raw import GSSError

from elogfetch.api.client import ElogClient
from elogfetch.exceptions import AuthenticationError

# GSS_S_NO_CRED (0xD0000) — "no credentials available"
_NO_CRED = GSSError(851968, 0)


def test_kinit_fails_raises_authentication_error():
    """When there's no ticket and kinit itself fails, AuthenticationError is raised."""
    with (
        patch("elogfetch.api.client._get_negotiate_token", side_effect=_NO_CRED),
        patch(
            "elogfetch.api.client.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "kinit"),
        ),
    ):
        client = ElogClient()
        with pytest.raises(AuthenticationError, match="kinit"):
            client._get_auth_headers()


def test_kinit_succeeds_then_gss_fails_raises_authentication_error():
    """When kinit runs but token generation still fails, AuthenticationError is raised."""
    with (
        patch("elogfetch.api.client._get_negotiate_token", side_effect=_NO_CRED),
        patch("elogfetch.api.client.subprocess.run"),
    ):
        client = ElogClient()
        with pytest.raises(AuthenticationError, match="after kinit"):
            client._get_auth_headers()
