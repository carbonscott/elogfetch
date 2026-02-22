
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)

_AUTH_PREFIX = "/ws-kerb/lgbk"
_PUBLIC_PREFIX = "/ws/lgbk"


class Endpoint(Generic[M]):
    """Typed API endpoint descriptor.

    pattern      — URL template using Python {param} placeholders
    model        — Pydantic response class to validate the JSON response against
    require_auth — if None, auto-detected: True when "{experiment_name}" is in pattern
    """

    def __init__(
        self,
        pattern: str,
        model: type[M],
        *,
        require_auth: bool | None = None,
    ) -> None:
        self.pattern = pattern
        self.model = model
        self._require_auth = require_auth

    @property
    def require_auth(self) -> bool:
        if self._require_auth is not None:
            return self._require_auth
        return "{experiment_name}" in self.pattern

    def url(self, **kwargs: Any) -> str:
        prefix = _AUTH_PREFIX if self.require_auth else _PUBLIC_PREFIX
        return prefix + self.pattern.format_map(kwargs)
