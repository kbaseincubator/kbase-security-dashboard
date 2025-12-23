"""
CDM task service endpoints.
"""

import datetime
from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from pydantic import BaseModel, Field
from typing import Annotated

from kbase._security_dashboard.service import app_state
from kbase._security_dashboard.service.exceptions import UnauthorizedError
from kbase._security_dashboard.git_commit import GIT_COMMIT
from kbase._security_dashboard.service.http_bearer import KBaseHTTPBearer
from kbase._security_dashboard.version import VERSION
from kbase._security_dashboard.service.timestamp import utcdatetime
from kbase._security_dashboard.service.user import SecDBUser, SecDBRole

NOTES = "This service is a prototype"

ROUTER_GENERAL = APIRouter(tags=["General"])

_AUTH = KBaseHTTPBearer()


def _ensure_admin(user: SecDBUser, err_msg: str):
    if not user.is_full_admin():
        raise UnauthorizedError(err_msg)


class Root(BaseModel):
    """ General information about the service """
    service_name: Annotated[str, Field(description="The name of the service.")]
    version: Annotated[str, Field(
        examples=[VERSION], description="The semantic version of the service."
    )]
    git_hash: Annotated[str, Field(
        examples=["b78f6e15e85381a7df71d6005d99e866f3f868dc"],
        description="The git commit of the service code."
    )]
    server_time: Annotated[datetime.datetime, Field(
        examples=["2022-10-07T17:58:53.188698Z"],
        description="The server's time as an ISO8601 string."
    )]
    notes: Annotated[str, Field(description="Notes about the service.")]


@ROUTER_GENERAL.get(
    "/",
    response_model=Root,
    summary="General service info",
    description="General information about the service.")
async def root(r: Request) -> Root:
    return {
        "service_name": app_state.get_app_state(r).service_name,
        "version": VERSION,
        "git_hash": GIT_COMMIT,
        "server_time": utcdatetime(),
        "notes": NOTES,
    }

class WhoAmI(BaseModel):
    """ Information about the user. """
    user: Annotated[str, Field(examples=["kbasehelp"], description="The user's username.")]
    roles: Annotated[list[SecDBRole], Field(
        examples=[[SecDBRole.FULL_ADMIN]], description="The users's roles for the service."
    )]


@ROUTER_GENERAL.get(
    "/whoami/",
    response_model=WhoAmI,
    summary="Who am I? What does it all mean?",
    description="Information about the current user."
)
async def whoami(r: Request, user: SecDBUser=Depends(_AUTH)) -> WhoAmI:
    return WhoAmI(user=user.user, roles=user.roles)
