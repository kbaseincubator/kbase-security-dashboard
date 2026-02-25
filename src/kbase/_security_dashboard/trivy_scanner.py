"""
Utilities for running Trivy security scans on container images.
"""

import json
import logging
import os
import subprocess
from typing import NamedTuple


class TrivyScanResult(NamedTuple):
    """
    Results from a Trivy container image scan.
    """
    critical: int
    """ Number of critical severity vulnerabilities """

    high: int
    """ Number of high severity vulnerabilities """

    medium: int
    """ Number of medium severity vulnerabilities """

    low: int
    """ Number of low severity vulnerabilities """


def scan_container_image(
    image_name: str,
    github_token: str | None = None
) -> TrivyScanResult:
    """
    Run a Trivy scan on a container image and return vulnerability counts.

    image_name - Full image name (e.g., ghcr.io/kbase/auth2:latest)
    github_token - Optional GitHub token for authenticating to private registries

    Returns TrivyScanResult with counts by severity.
    Raises subprocess.CalledProcessError if trivy scan fails.
    """
    logr = logging.getLogger(__name__)

    logr.info(f"Running Trivy scan on {image_name}")

    # Build trivy command
    cmd = [
        "trivy", "image",
        "--format", "json",
        "--quiet",
        "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
        image_name
    ]

    # Set up environment with authentication if token provided
    env = os.environ.copy()
    if github_token:
        env["TRIVY_USERNAME"] = "token"
        env["TRIVY_PASSWORD"] = github_token

    # Run trivy
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
    except subprocess.CalledProcessError as e:
        # Log stdout and stderr for debugging
        logr.error(
            f"Trivy scan failed for {image_name} with exit code {e.returncode}\n"
            f"stdout: {e.stdout}\n"
            f"stderr: {e.stderr}"
        )
        raise

    # Parse JSON output
    data = json.loads(result.stdout)

    # Count vulnerabilities by severity
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for result_entry in data.get("Results", []):
        vulnerabilities = result_entry.get("Vulnerabilities") or []
        for vuln in vulnerabilities:
            severity = vuln.get("Severity", "").upper()
            if severity in counts:
                counts[severity] += 1

    logr.info(
        f"Trivy scan complete for {image_name}: "
        f"critical={counts['CRITICAL']}, high={counts['HIGH']}, "
        f"medium={counts['MEDIUM']}, low={counts['LOW']}"
    )

    return TrivyScanResult(
        critical=counts["CRITICAL"],
        high=counts["HIGH"],
        medium=counts["MEDIUM"],
        low=counts["LOW"]
    )
