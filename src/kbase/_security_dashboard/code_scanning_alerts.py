"""
Fetches Code Scanning alert data from GitHub.

Code Scanning alerts are branch-specific (e.g., from Trivy, CodeQL).
"""

from collections import defaultdict
from dataclasses import dataclass
import logging
import requests


_GITHUB_API_URL = "https://api.github.com"
_PER_PAGE = 100

# Map severity levels to standardized names
_SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low"
}
_IGNORE_SEVERITY = {"note"}


def _get_severity(severity: str) -> str:
    if severity in _IGNORE_SEVERITY:
        return None
    if severity.lower() not in _SEVERITY_MAP:
        raise ValueError("unknown severity: " + severity)
    return _SEVERITY_MAP[severity.lower()]


@dataclass
class CodeScanningAlertsSnapshot:
    """
    Snapshot of Code Scanning alerts for a specific branch.

    Code Scanning alerts are branch-specific (unlike Dependabot alerts).
    """

    owner_org: str
    """ The repo owner or organization. """

    repo: str
    """ The repo name. """

    branch: str
    """ The branch this snapshot corresponds to (main/master/develop). """

    critical: int
    """ Number of critical severity vulnerabilities. """

    high: int
    """ Number of high severity vulnerabilities. """

    medium: int
    """ Number of medium severity vulnerabilities. """

    low: int
    """ Number of low severity vulnerabilities. """


def _parse_link_header(link_header: str) -> str | None:
    """
    Parse the Link header to find the next page URL.

    Returns the next URL or None if no next page.
    """
    # Note: this is ass
    if not link_header:
        return None

    for link in link_header.split(","):
        if 'rel="next"' in link:
            return link[link.find("<") + 1 : link.find(">")]
    return None


def get_code_scanning_alerts_snapshot(
    owner_or_org: str,
    repo: str,
    branch: str,
    github_token: str,
) -> CodeScanningAlertsSnapshot:
    """
    Get a snapshot of open Code Scanning alerts for a specific branch.

    owner_or_org - the owner or organization that owns the repo
    repo - the repo name
    branch - the branch name (main, master, or develop)
    github_token - GitHub personal access token. Note this must
        be a classic token to access repos you don't own

    Returns a CodeScanningAlertsSnapshot with counts by severity level.
    """
    logr = logging.getLogger(__name__)

    logr.info(f"Fetching Code Scanning alerts for {owner_or_org}/{repo} ({branch})")

    headers = {"Authorization": f"Bearer {github_token}"}

    # Filter by branch using the ref parameter
    url = (f"{_GITHUB_API_URL}/repos/{owner_or_org}/{repo}/code-scanning/alerts"
        + f"?state=open&ref=refs/heads/{branch}&per_page={_PER_PAGE}"
    )
    severity_counts = defaultdict(int)
    page = 1

    while url:
        logr.info(
            f"Fetching page {page} of Code Scanning alerts for {owner_or_org}/{repo} ({branch})"
        )
        res = requests.get(url, headers=headers)
        res.raise_for_status()

        alerts = res.json()

        if not alerts:
            logr.info(f"No more Code Scanning alerts on page {page}")
            break

        for alert in alerts:
            # Code scanning uses "rule.severity" or falls back to "rule.security_severity_level"
            severity = (
                alert.get("rule", {}).get("security_severity_level") or
                alert.get("rule", {}).get("severity") or
                ""
            ).lower()
            sev = _get_severity(severity)
            if sev:
                severity_counts[sev] += 1

        url = _parse_link_header(res.headers.get("link"))
        page += 1

    snapshot = CodeScanningAlertsSnapshot(
        owner_org=owner_or_org,
        repo=repo,
        branch=branch,
        critical=severity_counts.get("critical", 0),
        high=severity_counts.get("high", 0),
        medium=severity_counts.get("medium", 0),
        low=severity_counts.get("low", 0),
    )

    logr.info(
        f"Code Scanning alerts for {owner_or_org}/{repo} ({branch}): "
        f"critical={snapshot.critical}, high={snapshot.high}, "
        f"medium={snapshot.medium}, low={snapshot.low}"
    )

    return snapshot
