"""
Trivy security scanning for container images in GitHub Container Registry.
"""

from dataclasses import dataclass
import logging

from kbase._security_dashboard.image_util import get_latest_container_image
from kbase._security_dashboard.trivy_scanner import scan_container_image


@dataclass
class TrivySnapshot:
    """
    A snapshot of Trivy scan results for a container image.
    """

    owner_org: str
    """ The repo owner or organization. """

    repo: str
    """ The repo name. """

    branch: str
    """ The branch this image corresponds to (main/master/develop). """

    image_tags: list[str]
    """ All tags for the image that was scanned (e.g., ['latest', 'v1.2.3']). """

    critical: int
    """ Number of critical severity vulnerabilities. """

    high: int
    """ Number of high severity vulnerabilities. """

    medium: int
    """ Number of medium severity vulnerabilities. """

    low: int
    """ Number of low severity vulnerabilities. """


def get_trivy_snapshot(
    owner_or_org: str,
    repo: str,
    branch: str,
    github_token: str,
) -> TrivySnapshot | None:
    """
    Get a Trivy scan snapshot for a repo's container image.

    Looks up the latest container image for the repo/branch in GitHub Container Registry,
    then runs a Trivy scan on it.

    owner_or_org - the owner or organization that owns the repo
    repo - the repo name
    branch - the branch name (main, master, or develop)
    github_token - GitHub personal access token with read:packages scope.
        Note this must be a classic token to access repos you don't own.

    Returns a TrivySnapshot with vulnerability counts by severity level,
    or None if no container image exists for this repo/branch.

    Raises requests.HTTPError for GitHub API errors.
    Raises subprocess.CalledProcessError if Trivy scan fails.
    """
    logr = logging.getLogger(__name__)

    logr.info(f"Getting Trivy snapshot for {owner_or_org}/{repo} ({branch})")

    # Find the latest image
    image = get_latest_container_image(owner_or_org, repo, branch, github_token)

    if not image:
        # No container package or no tagged images - this is normal for repos without containers
        return None

    # Scan the image
    scan_result = scan_container_image(image.image_name, github_token)

    # Create snapshot
    snapshot = TrivySnapshot(
        owner_org=owner_or_org,
        repo=repo,
        branch=branch,
        image_tags=image.tags,
        critical=scan_result.critical,
        high=scan_result.high,
        medium=scan_result.medium,
        low=scan_result.low,
    )

    logr.info(
        f"Trivy snapshot for {owner_or_org}/{repo} ({branch}, tags={image.tags}): "
        f"critical={snapshot.critical}, high={snapshot.high}, "
        f"medium={snapshot.medium}, low={snapshot.low}"
    )

    return snapshot
