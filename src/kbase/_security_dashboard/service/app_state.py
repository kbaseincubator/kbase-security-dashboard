"""
Functions for creating and handling application state.

All functions assume that the application state has been appropriately initialized via
calling the build_app() method
"""

import asyncio
from dataclasses import dataclass
from fastapi import FastAPI, Request
from kbase.auth import AsyncKBaseAuthClient
import logging
from typing import NamedTuple, Any

from kbase._security_dashboard.service.scheduler import RepoETLScheduler
from kbase._security_dashboard.service.user import SecDBAuth, SecDBUser

# The main point of this module is to handle all the application state in one place
# to keep it consistent and allow for refactoring without breaking other code


@dataclass(frozen=True, kw_only=True)
class AppState():
    """ Holds general application state. """
    service_name: str
    """ The name of the service. """
    auth: SecDBAuth
    """ The authentication client for the service. """
    sched: RepoETLScheduler
    """ The scheduler for the ETL process. """


class RequestState(NamedTuple):
    """ Holds request specific state. """
    user: SecDBUser | None
    token: str | None


async def build_app(app: FastAPI, cfg: dict[str, Any], service_name: str):
    """
    Build the application state.

    app - the FastAPI app.
    cfg - the service config.
    service_name - the name of the service.
    """
    logr = logging.getLogger(__name__)
    logr.info("Connecting to KBase auth service... ")
    kbauth = await AsyncKBaseAuthClient.create(cfg["auth"]["url"])
    auth = SecDBAuth(
        kbauth,
        set([r.strip() for r in cfg["auth"]["admin_roles_full"].split(",")]),
    )
    logr.info("Done")
    sched = None
    try:
        logr.info("Bulding scheduler")
        psg = cfg["postgres"]
        sched = RepoETLScheduler(
            cron_string=cfg["service"]["schedule_cron"],
            github_token=cfg["github"]["token"],
            repos=cfg["repos"],
            postgres_host=psg["host"],
            postgres_port=psg["port"],
            postgres_database=psg["database"],
            postgres_user=psg["user"] or None,
            postgres_password=psg["password"] or None,
        )
        logr.info("Done")
        app.state._auth = kbauth
        app.state._sched = sched
        app.state._sdbstate = AppState(
            service_name=service_name,
            auth=auth,
            sched=sched,
        )
    
    except Exception:
        await kbauth.close()
        if sched:
            sched.close()
        raise


def get_app_state(r: Request) -> AppState:
    """
    Get the application state from a request.
    """
    if not r.app.state._sdbstate:
        raise ValueError("App state has not been initialized")
    return r.app.state._sdbstate


async def destroy_app_state(app: FastAPI):
    """
    Destroy the application state, shutting down services and releasing resources.
    """
    await app.state._auth.close()
    app.state._sched.close()
    # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
    await asyncio.sleep(0.250)


def set_request_user(r: Request, user: SecDBUser | None, token: str | None):
    """ Set the user for the current request. """
    # if we add more stuff in the request state we'll need to not blow away the old state
    r.state._sdbstate = RequestState(user=user, token=token)


def _get_request_state(r: Request, field: str) -> RequestState:
    if not getattr(r.state, "_sdbstate", None) or not r.state._sdbstate:
        return None
    return getattr(r.state._sdbstate, field)


def get_request_user(r: Request) -> SecDBUser:
    """ Get the user for a request. """
    return _get_request_state(r, "user")


def get_request_token(r: Request) -> str:
    """ Get the token for a request. """
    return _get_request_state(r, "token")
