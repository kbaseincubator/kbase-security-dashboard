"""
Error codes for exceptions thrown by the security dashboard service system.
"""

from enum import Enum


class ErrorType(Enum):
    """
    The type of an error, consisting of an error code and a brief string describing the type.
    :ivar error_code: an integer error code.
    :ivar error_type: a brief string describing the error type.
    """

    AUTHENTICATION_FAILED =      (10000, "Authentication failed")
    """ A general authentication error. """

    NO_TOKEN =                   (10010, "No authentication token")
    """ No token was provided when required. """

    INVALID_TOKEN =              (10020, "Invalid token")
    """ The token provided is not valid. """

    INVALID_AUTH_HEADER =        (10030, "Invalid authentication header")
    """ The authentication header is not valid. """
    
    UNAUTHORIZED =               (20000, "Unauthorized")
    """ The user is not authorized to perform the requested action. """
    
    REQUEST_VALIDATION_FAILED =  (30010, "Request validation failed")
    """ A request to a service failed validation of the request. """
    
    NOT_FOUND =                  (40000, "Not Found")
    """ The requested resource was not found. """

    def __init__(self, error_code, error_type):
        self.error_code = error_code
        self.error_type = error_type
