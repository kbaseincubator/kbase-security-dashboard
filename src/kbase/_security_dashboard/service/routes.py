"""
CDM task service endpoints.
"""

import datetime
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, AwareDatetime
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
ROUTER_REPO_ETL = APIRouter(tags=["Repo ETL"])

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


class NextRun(BaseModel):
    """ Information about the next run of the ETL process. """
    next_run: Annotated[AwareDatetime, Field(
        examples=[utcdatetime()],
        description="The time at which the ETL process is next scheduled to run."
    )]


@ROUTER_REPO_ETL.get(
    "/next_run/",
    response_model=NextRun,
    summary="Get the time of the next run.",
    description="Get the time the next ETL process run is scheduled to occur."
)
async def next_run(r: Request, user: SecDBUser=Depends(_AUTH)) -> NextRun:
    _ensure_admin(user, "Only service admins can perform this operation")
    nr = app_state.get_app_state(r).sched.get_next_runtime()
    return NextRun(next_run=nr)


class LastResult(BaseModel):
    """ The last result of running the codecov / github ETL process.. """
    time_complete: Annotated[AwareDatetime | None, Field(
        example=[utcdatetime()],
        description="The time the ETL process ran, or null if it has not yet run since the "
           + "service started."
    )] = None
    exception: Annotated[str | None, Field(
        description="The exception that occurred during the ETL run or null if the run was "
            + "successful or there has not been a run yet"
    )]


@ROUTER_REPO_ETL.get(
    "/last_result/",
    response_model=LastResult,
    summary="Get the result of the last ETL run.",
    description="Get the result of the last ETL run. If the run failed, a 500 is returned."
)
async def last_result(r: Request, user: SecDBUser=Depends(_AUTH)) -> LastResult | JSONResponse:
    _ensure_admin(user, "Only service admins can perform this operation")
    res = app_state.get_app_state(r).sched.result
    lr = LastResult(time_complete=res.time_complete, exception=res.exception)
    if res.exception:
        return JSONResponse(content=lr.model_dump(mode="json"), status_code=500)
    return lr


@ROUTER_REPO_ETL.post(
    "/enqueue_run/",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Enqueue an ETL run.",
    description="Start an ETL run if one is not already running. If an ETL process is running "
        + "this call is a no-op."
)
async def enqueue_run(r: Request, user: SecDBUser=Depends(_AUTH)):
    _ensure_admin(user, "Only service admins can perform this operation")
    app_state.get_app_state(r).sched.run_now()
