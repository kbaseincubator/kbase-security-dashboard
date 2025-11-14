"""
Fetches coverage history from codecov.
"""

from collections import defaultdict
import dateutil
from dataclasses import dataclass
import datetime
import logging
import math
import requests
from typing import Any


_PAGE_SIZE = 100
_CODECOV_URL = (
    "https://api.codecov.io/api/v2/github/{owner}/repos/{repo}/commits/?page_size="
    + str(_PAGE_SIZE)
)


@dataclass
class CommitCoverage:
    
    commit_id: str
    """ The ID of the commit. """
    
    timestamp: datetime.datetime
    """ The commit's timestamp. """
    
    coverage: float
    """ The commit's coverage. """


@dataclass
class CoverageData:
    
    owner_org: str
    """ The rpeo owner or organization. """
    
    repo: str
    """ The repo for the coverage data. """
    
    coverage: dict[str, list[CommitCoverage]]
    """ The coverage data - a dict of branch to coverage data. """


def _process_commit(commit: dict[str, Any], branches: set[str] | None) -> bool:
    return (
        commit["ci_passed"]
        and commit["state"] == "complete"
        and (not branches or commit["branch"] in branches)
    )


def get_coverage_history(
    owner_or_org: str,
    repo: str,
    branches: set[str] | None = None,
    since: datetime.datetime | None = None,
) -> dict[str, list[CommitCoverage]]:
    """
    Get the coverage history for a github reoo.
    
    owner_or_org - the owner or the organization that owns the repo.
    repo - the repo name.
    branches - only return data for the given branches.
    since - only return data since the given date.
    
    Returns a dictionary of the git branch to a list of commits for that branch.
    """
    # Could maybe optimize by going branch by branch, esp if there's only one branch.
    # This will be running weekly-ish so don't worry about it for now
    logr = logging.getLogger(__name__)
    next_url = _CODECOV_URL.format(owner=owner_or_org, repo=repo)
    ret = defaultdict(list)
    page = 1
    while next_url:
        res = requests.get(next_url)
        res.raise_for_status()
        js = res.json()
        pages = math.ceil(js["count"] / _PAGE_SIZE)
        logr.info(
            f"Fetched page {page} of {pages} pages for {js['count']} "
            + f"records for repo {owner_or_org}/{repo}"
        )
        page += 1
        for r in js["results"]:
            if _process_commit(r, branches):
                timestamp=dateutil.parser.isoparse(r["timestamp"])
                # assumes results are sorted by date, which seems to be the case
                # Not documented as such... https://docs.codecov.com/reference/repos_commits_list
                if since and timestamp < since:
                    logr.info(f"Hit 'since' limit of {since}, pulling no more records")
                    return CoverageData(owner_org=owner_or_org, repo=repo, coverage=dict(ret))
                ret[r["branch"]].append(CommitCoverage(
                    commit_id=r["commitid"],
                    timestamp=timestamp,
                    coverage=r["totals"]["coverage"],
                ))
        next_url = js["next"]
    return CoverageData(owner_org=owner_or_org, repo=repo, coverage=dict(ret))
