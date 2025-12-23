"""
Map errors from exception type to custom error type and HTTP status. 
"""

from fastapi import status
from kbase.auth import InvalidTokenError, InvalidUserError
from typing import NamedTuple

from kbase._security_dashboard.service.errors import ErrorType
from kbase._security_dashboard.service.exceptions import (
    InvalidAuthHeaderError,
    UnauthorizedError,
)
from kbase._security_dashboard.service.http_bearer import MissingTokenError

_H400 = status.HTTP_400_BAD_REQUEST
_H401 = status.HTTP_401_UNAUTHORIZED
_H403 = status.HTTP_403_FORBIDDEN
_H404 = status.HTTP_404_NOT_FOUND


class ErrorMapping(NamedTuple):
    """ The application error type and HTTP status code for an exception. """
    err_type: ErrorType | None
    """ The type of application error. None if a 5XX error or Not Found based on the url."""
    http_code: int
    """ The HTTP code of the error. """


_ERR_MAP = {
    MissingTokenError: ErrorMapping(ErrorType.NO_TOKEN, _H401),
    InvalidAuthHeaderError: ErrorMapping(ErrorType.INVALID_AUTH_HEADER, _H401),
    InvalidTokenError: ErrorMapping(ErrorType.INVALID_TOKEN, _H401),
    UnauthorizedError: ErrorMapping(ErrorType.UNAUTHORIZED, _H403),
}


def map_error(err: Exception) -> ErrorMapping:
    """
    Map an error to an optional error type and a HTTP code.
    """
    # May need to add code to go up the error hierarchy if multiple errors have the same type
    ret = _ERR_MAP.get(type(err))
    if not ret:
        ret = ErrorMapping(None, status.HTTP_500_INTERNAL_SERVER_ERROR)
    return ret
