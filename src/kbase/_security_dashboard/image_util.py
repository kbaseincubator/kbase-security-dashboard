"""
Utilities for interacting with GitHub Container Registry packages.
"""

import logging
import requests
from datetime import datetime
from typing import NamedTuple, Any


_GITHUB_API_URL = "https://api.github.com"


class ContainerImage(NamedTuple):
    """
    Represents a container image in GitHub Container Registry.
    """
    image_name: str
    """ Full image name (e.g., ghcr.io/kbase/auth2:abc123) """

    tags: list[str]
    """ All tags for this image (e.g., ['latest', 'v1.2.3', 'abc123']) """

    created_at: datetime
    """ Timestamp when the image was created """


def _validate_package_404(
    response: requests.Response,
    org: str,
    repo: str,
    url: str,
    headers: dict
) -> None:
    """
    Handle 404 response from package API, distinguishing between missing package
    (normal) and missing repo (config error).

    Raises requests.HTTPError if repo doesn't exist or if 404 is not package-related.
    """
    logr = logging.getLogger(__name__)

    # Verify this is a package-related 404, not a bad URL
    try:
        error_data = response.json()
    except Exception:
        # Couldn't parse error response, treat as unexpected 404
        logr.error(f"Could not parse 404 response from {url}:\n{response.text}")
        response.raise_for_status()

    message = error_data.get("message", "").lower()
    if "package" not in message or "not found" not in message:
        # Not a package error - unexpected, so raise
        logr.error(f"Unexpected 404 for {url}: {message}")
        response.raise_for_status()

    # It's a "package not found" error - could mean no package or repo doesn't exist
    # Check if repo exists to distinguish config errors from missing packages
    repo_url = f"{_GITHUB_API_URL}/repos/{org}/{repo}"
    logr.debug(f"Got package not found, checking if repo exists: {org}/{repo}")
    repo_response = requests.get(repo_url, headers=headers)

    if repo_response.status_code == 404:
        logr.error(f"Repository not found: {org}/{repo} (check configuration)")

    repo_response.raise_for_status()  # Raise for 404 or any other errors


def _find_best_tag(tags: list[str]) -> str:
    """
    Select the best tag from a list.
    Prefers non-latest tags to avoid race conditions where latest tag moves.
    """
    # Prefer non-latest tags to avoid race conditions where latest moves
    # between discovery and scanning
    non_latest_tags = [t for t in tags if not t.startswith("latest")]
    if non_latest_tags:
        return non_latest_tags[0]

    # All tags are latest-variants, pick the shortest (likely just "latest")
    return min(tags, key=len)


def _find_tagged_version(
    versions: list[dict[str, Any]], org: str, package_name: str
) -> ContainerImage | None:
    """
    Find the first version with tags from a list of package versions.

    Returns ContainerImage if found, None otherwise.
    """
    logr = logging.getLogger(__name__)

    for version in versions:
        metadata = version.get("metadata", {}).get("container", {})
        tags = metadata.get("tags", [])

        if tags:
            primary_tag = _find_best_tag(tags)
            created_at = datetime.fromisoformat(version.get("created_at"))
            # GitHub Container Registry normalizes all names to lowercase
            image_name = f"ghcr.io/{org.lower()}/{package_name.lower()}:{primary_tag}"

            logr.info(f"Found image: {image_name} (tags: {tags}, created: {created_at})")

            return ContainerImage(
                image_name=image_name,
                tags=tags,
                created_at=created_at
            )

    return None


def get_latest_container_image(
    org: str,
    repo: str,
    branch: str,
    github_token: str
) -> ContainerImage | None:
    """
    Find the latest container image for a repo based on naming convention.

    Naming convention:
    - main/master branch: package name = repo name
    - develop branch: package name = {repo}-develop

    org - GitHub organization
    repo - Repository name
    branch - Branch name (main, master, or develop)
    github_token - GitHub personal access token with read:packages scope

    Returns ContainerImage if found, None if package doesn't exist or has no tagged versions.
    Raises requests.HTTPError if repo doesn't exist (likely config error).
    Raises requests.HTTPError for other API errors.
    """
    logr = logging.getLogger(__name__)

    # Map branch to package name
    if branch in ["main", "master"]:
        package_name = repo
    elif branch == "develop":
        package_name = f"{repo}-develop"
    else:
        raise ValueError(f"Unsupported branch: {branch}")

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get package versions (these are individual image pushes)
    # Use per_page=100 to reduce likelihood of missing tagged images on later pages
    url = f"{_GITHUB_API_URL}/orgs/{org}/packages/container/{package_name}/versions"
    params = {"per_page": 100}

    logr.info(f"Fetching container versions for {org}/{package_name}")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 404:
        _validate_package_404(response, org, repo, url, headers)
        # Repo exists, so 404 means no package - this is normal
        logr.info(f"No container package found for {org}/{package_name}")
        return None

    response.raise_for_status()
    versions = response.json()

    # Find the first version with tags
    result = _find_tagged_version(versions, org, package_name)
    if result:
        return result

    # No tagged versions found on first page
    # Check if there are more pages - if so, there might be tagged images we're missing
    link_header = response.headers.get("Link", "")
    if "rel=\"next\"" in link_header:
        logr.warning(
            f"No tagged versions found on first page for {org}/{package_name}, "
            f"but more pages exist. Consider implementing full pagination if this is a problem."
        )
    else:
        logr.info(f"No tagged versions found for {org}/{package_name}")
    return None
