"""
Fetches open Dependabot PRs from GitHub.
"""

from dataclasses import dataclass
import logging
import re
from typing import Any

import requests


_GITHUB_API_URL = "https://api.github.com"
_PER_PAGE = 100


@dataclass
class DependabotSnapshot:

    owner_org: str
    """ The repo owner or organization. """

    repo: str
    """ The repo name. """

    total_prs: int
    """ Total number of open Dependabot PRs. """

    total_dependencies: int
    """ Total number of dependencies with updates (accounting for grouped PRs). """

    grouped_prs: int
    """ Number of PRs that update multiple dependencies. """

    single_prs: int
    """ Number of PRs that update a single dependency. """


def _is_dependabot_pr(pr: dict[str, Any]) -> bool:
    """Check if a PR is from Dependabot."""
    user = pr.get("user", {})
    return user.get("login") in ["dependabot[bot]", "dependabot-preview[bot]"]


def _count_dependencies_in_pr(pr: dict[str, Any]) -> int:
    """
    Count the number of dependencies updated in a PR.
    
    Grouped PRs will have a title like:
    "Bump the npm-dependencies group with 3 updates"
    "Bump the production-dependencies group across 1 directory with 5 updates"
    
    Single dependency PRs have titles like:
    "Bump pytest from 7.0.0 to 7.1.0"
    """
    title = pr.get("title", "")
    
    # Check for grouped PR pattern
    # Patterns: "with X updates", "with X update"
    match = re.search(r'with (\d+) updates?', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # otherwise
    return 1


def get_dependabot_snapshot(
    owner_or_org: str,
    repo: str,
    github_token: str | None = None,
) -> DependabotSnapshot:
    """
    Get a snapshot of open Dependabot PRs for a GitHub repo.

    owner_or_org - the owner or organization that owns the repo
    repo - the repo name
    github_token - optional GitHub personal access token for higher rate limits

    Returns a DependabotSnapshot with counts of open PRs and dependencies.
    """
    logr = logging.getLogger(__name__)
    
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    # Get all open PRs
    url = f"{_GITHUB_API_URL}/repos/{owner_or_org}/{repo}/pulls"
    params = {
        "state": "open",
        "per_page": _PER_PAGE,
        "page": 1
    }
    
    all_prs = []
    while True:
        logr.info(f"Fetching page {params['page']} of open PRs for {owner_or_org}/{repo}")
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        
        prs = res.json()
        if not prs:
            break
        
        all_prs.extend(prs)
        
        # Check if there are more pages
        if len(prs) < _PER_PAGE:
            break
        
        params["page"] += 1
    
    # Filter for Dependabot PRs and analyze
    dependabot_prs = [pr for pr in all_prs if _is_dependabot_pr(pr)]
    
    total_dependencies = 0
    grouped_prs = 0
    single_prs = 0
    
    for pr in dependabot_prs:
        dep_count = _count_dependencies_in_pr(pr)
        total_dependencies += dep_count
        
        if dep_count > 1:
            grouped_prs += 1
        else:
            single_prs += 1
    
    logr.info(
        f"Found {len(dependabot_prs)} Dependabot PRs for {owner_or_org}/{repo}: "
        f"{single_prs} single, {grouped_prs} grouped, {total_dependencies} total dependencies"
    )
    
    return DependabotSnapshot(
        owner_org=owner_or_org,
        repo=repo,
        total_prs=len(dependabot_prs),
        total_dependencies=total_dependencies,
        grouped_prs=grouped_prs,
        single_prs=single_prs,
    )
