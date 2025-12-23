"""
Alteration of FastAPI's HTTPBearer class to handle the KBase authorization steps.

Also adds an `optional` keyword argument that allows for missing auth. If true and no
authorization information is provided, `None` is returned as the user.
"""

from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.requests import Request
from fastapi.security.http import HTTPBase
from typing import Optional

from kbase._security_dashboard.service import app_state
from kbase._security_dashboard.service.user import SecDBUser

# Modified from https://github.com/tiangolo/fastapi/blob/e13df8ee79d11ad8e338026d99b1dcdcb2261c9f/fastapi/security/http.py#L100
# Basically the only reason for this class is to get the UI to work with auth.
# Dependent on the middleware in security_dashboard.py to set the user in the request state.

_SCHEME = "Bearer"


class KBaseHTTPBearer(HTTPBase):
    def __init__(
        self,
        *,
        bearerFormat: Optional[str] = None,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        # FastAPI uses auto_error, but that allows for malformed headers as well as just
        # no header. Use a different variable name since the behavior is different.
        optional: bool = False,
    ):
        self.model = HTTPBearerModel(bearerFormat=bearerFormat, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.optional = optional

    async def __call__(self, request: Request) -> SecDBUser:
        user = app_state.get_request_user(request)
        if not user and not self.optional:
            raise MissingTokenError("Authorization header required")
        return user


class MissingTokenError(Exception):
    """ An error thrown when a token is expected but not provided. """
