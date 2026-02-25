"""
Security Dashboard data collection script.

Reads configuration from TOML file and collects:
- Code coverage from Codecov
- Test status from GitHub Actions
- Dependabot PR counts
- Vulnerability counts (Dependabot + Code Scanning)
"""

import datetime
import logging
import psycopg2


from kbase._security_dashboard import codecov_load
from kbase._security_dashboard import gha_test_actions_load
from kbase._security_dashboard import dependabot_load
from kbase._security_dashboard import vulnerabilities_load
from kbase._security_dashboard import repo_metadata
from kbase._security_dashboard import trivy_load


def _init_all_tables(conn: psycopg2.extensions.connection):
    """Initialize all database tables."""
    logr = logging.getLogger(__name__)
    logr.info("Initializing database tables...")
    for mod in [
        codecov_load, gha_test_actions_load, dependabot_load, vulnerabilities_load,
        repo_metadata, trivy_load
    ]:
        mod.init_table(conn)
    logr.info("Database tables initialized")


def process_repos(
    conn: psycopg2.extensions.connection,
    github_token: str,
    repos: list[dict[str, str | list[str]]]
):
    """
    Process security data for a set of repos.
    
    conn - the postgres connection where the data will be stored.
    github_token - a GitHub personal access token. Note this must
        be a classic token to access repos you don't own
    repos - a list of repos. Each repo has the following keys:
        org - the github organization.
        repo  - the repo name.
        main_branch - the main branch name. Defaults to "main" if not present.
        dev_branch - the develop branch name. Defaults to "develop" if not present.
        test_workflows - a string or list of strings specifying which github action(s) are tests.
    """
    logr = logging.getLogger(__name__)
    for i, r in enumerate(repos):
        d = dict(r)
        if "main_branch" not in r:
            d["main_branch"] = "main"
        if "dev_branch" not in r:
            d["dev_branch"] = "develop"
        repos[i] = d
    
    _init_all_tables(conn)
    repo_metadata.upsert_repo_metadata(conn, repos)
    
    if not repos:
        raise ValueError("No repositories configured")
    
    logr.info(f"Processing {len(repos)} repositories...")
    
    for repo_config in repos:
        org = repo_config["org"]
        repo = repo_config["repo"]
        branches = {repo_config["main_branch"], repo_config["dev_branch"]}
        test_workflows = repo_config.get("test_workflows")
        
        logr.info(f"{'='*60}")
        logr.info(f"Processing {org}/{repo}")
        logr.info(f"{'='*60}")
        
        # Convert test_workflows to appropriate type
        if test_workflows is None:
            workflow_filter = None  # Use default regex
        elif isinstance(test_workflows, str):
            workflow_filter = test_workflows  # Regex string
        elif isinstance(test_workflows, list):
            workflow_filter = set(test_workflows)  # Exact names
        else:
            logr.error(f"Invalid test_workflows type for {org}/{repo}: {type(test_workflows)}")
            continue
        
        try:
            # 1. Sync coverage data
            logr.info(f"Syncing coverage data for {org}/{repo}...")
            codecov_load.sync_coverage_data(conn, org, repo, branches=branches)

            # 2. Take test status snapshot
            logr.info(f"Taking test status snapshot for {org}/{repo}...")
            gha_test_actions_load.take_snapshot(
                conn,
                org,
                repo,
                branches=branches,
                workflow_filter=workflow_filter,
                github_token=github_token
            )

            # Generate a single snapshot timestamp for this repo to enable cross-table queries
            snapshot_date = datetime.datetime.now(datetime.timezone.utc)
            logr.info(f"Snapshot timestamp: {snapshot_date}")

            # 3. Take Dependabot PR snapshot
            logr.info(f"Taking Dependabot PR snapshot for {org}/{repo}...")
            dependabot_load.take_snapshot(conn, org, repo, snapshot_date, github_token)

            # 4. Take vulnerability snapshot
            logr.info(f"Taking vulnerability snapshot for {org}/{repo}...")
            vulnerabilities_load.take_snapshot(conn, org, repo, snapshot_date, github_token)

            # 5. Take Trivy scan snapshot
            logr.info(f"Taking Trivy scan snapshot for {org}/{repo}...")
            trivy_load.take_snapshot(conn, org, repo, branches, snapshot_date, github_token)

            logr.info(f"✓ Completed {org}/{repo}")
            
        except Exception as e:
            logr.error(f"✗ Failed to process {org}/{repo}: {e}", exc_info=True)
            raise
    
    logr.info(f"\n{'='*60}")
    logr.info("All repositories processed")
    logr.info(f"{'='*60}")
