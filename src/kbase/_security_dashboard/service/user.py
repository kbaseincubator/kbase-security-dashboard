"""
Classes for dealing with service users.
"""

from dataclasses import dataclass, field
from enum import Enum
from kbase.auth import AsyncKBaseAuthClient

class SecDBRole(str, Enum):
    """ A role for the service a user may possess. """
    
    FULL_ADMIN = "full_admin"
    # add roles as needed


@dataclass(frozen=True)
class SecDBUser:
    """
    Represents a user of the Security Dashboard system.

    Attributes:
        user - the name of the user.
        roles - the set of roles assigned to the user.
    """
    user: str
    roles: frozenset[SecDBRole] = field(default_factory=frozenset)

    def __post_init__(self):
        # Convert roles to frozenset if it isn't one already
        if not isinstance(self.roles, frozenset):
            object.__setattr__(self, 'roles', frozenset(self.roles))
        # TODO CODE check args aren't None. Creating class here so YAGNI for now

    def is_full_admin(self):
        """ Returns true if the user is a service admin with full rights to everything. """
        return SecDBRole.FULL_ADMIN in self.roles


class SecDBAuth:
    """ An authentication class for the serivice. """
    
    def __init__(
            self,
            kbaseauth: AsyncKBaseAuthClient,
            service_admin_roles: set[str],
    ):
        """
        Create the auth client.
        
        kbaseauth - a KBase authentication client.
        service_admin_roles - KBase auth roles that designates that a user is a service admin
            with full rights to everything.
        """
        if not kbaseauth:
            raise ValueError("kbaseauth is required")
        self._kbauth = kbaseauth
        self._admin_roles = service_admin_roles or []


    async def get_kbase_user(self, token: str) -> SecDBUser:
        """ Get a CTS user given a KBase token. """
        user = await self._kbauth.get_user(token)
        roles = set()
        has_roles = set(user.customroles)
        if has_roles & self._admin_roles:
            roles.add(SecDBRole.FULL_ADMIN)
        return SecDBUser(user=user.user, roles=roles)
