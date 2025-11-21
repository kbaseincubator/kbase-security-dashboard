"""
Fetches GitHub Actions test workflow status.
"""

from dataclasses import dataclass
from dateutil import parser
import datetime
import logging
import re
import requests
from typing import Any


_GITHUB_API_URL = "https://api.github.com"
_PER_PAGE = 100
_DEFAULT_WORKFLOW_PATH_REGEX = re.compile(r'(?:^|[\s_/-])tests?(?:[\s_\.-]|$)')


@dataclass
class TestStatusSnapshot:
    
    timestamp: datetime.datetime
    """ When the workflow(s) completed (most recent if multiple). """
    
    workflow_paths: list[str]
    """ Paths of the workflow(s) included in this snapshot. """
    
    success: bool
    """ Whether all tracked workflows succeeded (AND of all statuses). """


@dataclass
class TestStatusData:
    
    owner_org: str
    """ The repo owner or organization. """
    
    repo: str
    """ The repo name. """
    
    snapshots: dict[str, TestStatusSnapshot]
    """ Map of branch name to test status snapshot. """


def _find_workflow_runs(
    owner_or_org: str,
    repo: str,
    branch: str,
    workflow_filter: str | set[str] | None,
    github_token: str | None,
) -> dict[str, dict[str, Any]]:
    logr = logging.getLogger(__name__)
    if not workflow_filter:
        pattern = _DEFAULT_WORKFLOW_PATH_REGEX
    elif isinstance(workflow_filter, str):
        pattern = re.compile(workflow_filter)
    else:
        target_workflows = set(workflow_filter)
        pattern = None
        logr.info(f"Using workflow filter {target_workflows}")
    if pattern:
        logr.info(f"Using workflow filter {pattern}")
    
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    # Find matching workflows - paginate through results
    matching_runs = {}  # workflow_name -> run
    url = f"{_GITHUB_API_URL}/repos/{owner_or_org}/{repo}/actions/runs"
    params = {
        "branch": branch,
        "per_page": _PER_PAGE,
    }
    page = 1
    while True:
        logr.info(
            f"Fetching page {page} of workflow runs for {owner_or_org}/{repo} branch {branch}"
        )
        params["page"] = page
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        
        data = res.json()
        workflow_runs = data.get("workflow_runs", [])
        
        if not workflow_runs:
            logr.info(f"No more workflow runs on page {page}")
            break
        
        for run in workflow_runs:
            # Skip incomplete runs
            if run.get("status") == "completed":
                workflow_path = run["path"]
                
                # Check if this workflow matches our criteria
                if pattern:
                    if pattern.search(workflow_path.lower()):
                        matching_runs[workflow_path] = run
                        logr.info(
                            f"Found matching workflow '{workflow_path}' with pattern '{pattern}'"
                        )
                        # Found our match, we're done
                        break
                else:
                    # For exact names, find the most recent run of each target workflow
                    if workflow_path in target_workflows and workflow_path not in matching_runs:
                        matching_runs[workflow_path] = run
                        logr.info(f"Found workflow '{workflow_path}'")
        
        # Check if we're done
        if pattern and matching_runs:
            # For pattern mode, stop after finding first match
            break
        elif not pattern and len(matching_runs) == len(target_workflows):
            # For list mode, stop when we've found all target workflows
            break
        
        # Check if there are more pages
        if len(workflow_runs) < _PER_PAGE:
            logr.info(f"Reached end of workflow runs at page {page}")
            break
        
        page += 1
    return matching_runs


def _get_branch_snapshot(
    owner_or_org: str,
    repo: str,
    branch: str,
    workflow_filter: str | set[str] | None,
    github_token: str | None,
) -> TestStatusSnapshot | None:
    logr = logging.getLogger(__name__)
    matching_runs = _find_workflow_runs(owner_or_org, repo, branch, workflow_filter, github_token)
    if not matching_runs:
        return None

    # Get the most recent completion time and AND all statuses
    most_recent_time = None
    all_success = True
    workflow_paths = []
    
    for workflow_path, run in matching_runs.items():
        workflow_paths.append(workflow_path)
        
        # Parse completion time
        completed_at = parser.isoparse(run["updated_at"])
        if most_recent_time is None or completed_at > most_recent_time:
            most_recent_time = completed_at
        
        # Check if successful
        if not run.get("conclusion") == "success":
            all_success = False
            logr.info(f"Workflow '{workflow_path}' status: {run.get('conclusion')}")
    
    logr.info(
        f"Snapshot for {owner_or_org}/{repo} branch {branch}: "
        f"{len(workflow_paths)} workflow(s), success={all_success}"
    )
    return TestStatusSnapshot(
        timestamp=most_recent_time,
        workflow_paths=workflow_paths,
        success=all_success,
    )


def get_test_status(
    owner_or_org: str,
    repo: str,
    branches: set[str],
    workflow_filter: str | set[str] | None = None,
    github_token: str | None = None,
) -> TestStatusData:
    r"""
    Get test status snapshots for one or more branches of a GitHub repo.
    
    owner_or_org - the owner or organization that owns the repo
    repo - the repo name
    branches - set of branch names to check (e.g., {'main', 'develop'})
    workflow_filter - a filter to match workflow paths. Either
        * a regex pattern string,  If a pattern is provided, only first matching workflow
          is returned. The default is (?:^|[\s_-])tests?(?:[\s_-]|$)
        * a set of exact workflow names to track.
    github_token - optional GitHub personal access token for higher rate limits
    
    Returns a TestStatusData with snapshots for each branch that has matching workflows.
    """
    logr = logging.getLogger(__name__)
    
    snapshots = {}
    
    for branch in branches:
        logr.info(f"Fetching test status for {owner_or_org}/{repo} branch {branch}")
        snapshot = _get_branch_snapshot(owner_or_org, repo, branch, workflow_filter, github_token)
        
        if snapshot:
            snapshots[branch] = snapshot
        else:
            logr.warning(f"No snapshot generated for branch {branch}")
    
    return TestStatusData(
        owner_org=owner_or_org,
        repo=repo,
        snapshots=snapshots,
    )
