"""
General exceptions used by multiple modules.
"""


class UnauthorizedError(Exception):
    """ An exception thrown when a user attempts a forbidden action. """


class InvalidAuthHeaderError(Exception):
    """ An error thrown when an authorization header is invalid. """
