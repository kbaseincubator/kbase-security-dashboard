"""
Fetches vulnerability data from GitHub Dependabot alerts and Code Scanning alerts.
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
class VulnerabilitySnapshot:

    owner_org: str
    """ The repo owner or organization. """

    repo: str
    """ The repo name. """

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


def _fetch_dependabot_alerts(
    owner_or_org: str,
    repo: str,
    github_token: str,
) -> dict[str, int]:
    """
    Fetch open Dependabot alerts and count by severity.
    
    Returns dict of severity -> count.
    """
    logr = logging.getLogger(__name__)
    
    headers = {"Authorization": f"Bearer {github_token}"}
    
    url = (f"{_GITHUB_API_URL}/repos/{owner_or_org}/{repo}/dependabot/alerts"
        + f"?state=open&per_page={_PER_PAGE}"
    )
    
    severity_counts = defaultdict(int)
    page = 1
    
    while url:
        logr.info(
            f"Fetching page {page} of Dependabot alerts for {owner_or_org}/{repo}"
        )
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        
        alerts = res.json()
        
        if not alerts:
            logr.info(f"No more Dependabot alerts on page {page}")
            break
        
        for alert in alerts:
            severity = alert.get("security_advisory", {}).get("severity", "").lower()
            sev = _get_severity(severity)
            if sev:
                severity_counts[sev] += 1
        
        url = _parse_link_header(res.headers.get("link"))
        page += 1
    
    logr.info(
        f"Found {sum(severity_counts.values())} open Dependabot alerts for {owner_or_org}/{repo}"
    )
    return dict(severity_counts)


def _fetch_code_scanning_alerts(
    owner_or_org: str,
    repo: str,
    github_token: str,
) -> dict[str, int]:
    """
    Fetch open Code Scanning alerts (e.g., from Trivy) and count by severity.
    
    Returns dict of severity -> count.
    """
    logr = logging.getLogger(__name__)
    
    headers = {"Authorization": f"Bearer {github_token}"}
    
    url = (f"{_GITHUB_API_URL}/repos/{owner_or_org}/{repo}/code-scanning/alerts"
        + f"?state=open&per_page={_PER_PAGE}"
    )
    severity_counts = defaultdict(int)
    page = 1
    
    while url:
        logr.info(
            f"Fetching page {page} of Code Scanning alerts for {owner_or_org}/{repo}"
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
    
    logr.info(
        f"Found {sum(severity_counts.values())} open Code Scanning alerts "
        + f"for {owner_or_org}/{repo}"
    )
    return dict(severity_counts)


def get_vulnerability_snapshot(
    owner_or_org: str,
    repo: str,
    github_token: str,
) -> VulnerabilitySnapshot:
    """
    Get a snapshot of open vulnerabilities for a GitHub repo.

    Combines Dependabot alerts and Code Scanning alerts (e.g., Trivy).

    owner_or_org - the owner or organization that owns the repo
    repo - the repo name
    github_token - GitHub personal access token. Note this must
        be a classic token to access repos you don't own

    Returns a VulnerabilitySnapshot with counts by severity level.
    """
    logr = logging.getLogger(__name__)
    
    logr.info(f"Fetching vulnerability snapshot for {owner_or_org}/{repo}")
    
    # Fetch both types of alerts
    dependabot_counts = _fetch_dependabot_alerts(owner_or_org, repo, github_token)
    code_scanning_counts = _fetch_code_scanning_alerts(owner_or_org, repo, github_token)
    
    # Combine counts
    combined_counts = defaultdict(int)
    for severity, count in dependabot_counts.items():
        combined_counts[severity] = count
    for severity, count in code_scanning_counts.items():
        combined_counts[severity] += count
    
    # Create snapshot
    snapshot = VulnerabilitySnapshot(
        owner_org=owner_or_org,
        repo=repo,
        critical=combined_counts.get("critical", 0),
        high=combined_counts.get("high", 0),
        medium=combined_counts.get("medium", 0),
        low=combined_counts.get("low", 0),
    )
    
    logr.info(
        f"Vulnerability snapshot for {owner_or_org}/{repo}: "
        + f"critical={snapshot.critical}, high={snapshot.high}, "
        + f"medium={snapshot.medium}, low={snapshot.low}"
    )
    
    return snapshot
