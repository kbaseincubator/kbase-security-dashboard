"""
Load GitHub Actions test status data into postgres.
"""

import logging
import psycopg2

from kbase._security_dashboard.gha_test_actions import (
    TestStatusData,
    TestStatusSnapshot,
    get_test_status,
)


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the branch_test_status table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_status (
                org_user       VARCHAR(255) NOT NULL,
                repo           VARCHAR(255) NOT NULL,
                branch         VARCHAR(255) NOT NULL,
                timestamp      TIMESTAMPTZ NOT NULL,
                workflow_paths TEXT[] NOT NULL,
                success        BOOLEAN NOT NULL,
                PRIMARY KEY (org_user, repo, branch, timestamp)
            )
        """)
        
        # Create index for time-series queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_status_date
                ON test_status (org_user, repo, branch, timestamp DESC)
        """)
        
        conn.commit()


def _save_snapshot(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    branch: str,
    snapshot: TestStatusSnapshot,
):
    """
    Insert a test status snapshot into the table.
    
    Does nothing on conflict (same repo/branch/timestamp already exists).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO test_status 
                (org_user, repo, branch, timestamp, workflow_paths, success)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_user, repo, branch, timestamp) DO NOTHING
            """,
            (
                owner_org,
                repo,
                branch,
                snapshot.timestamp,
                snapshot.workflow_paths,
                snapshot.success,
            )
        )
        conn.commit()


def save_test_status(
    conn: psycopg2.extensions.connection,
    test_status_data: TestStatusData,
):
    """
    Insert test status snapshots for all branches into the table.
    
    Does nothing on conflict for each snapshot.
    """
    logr = logging.getLogger(__name__)
    
    for branch, snapshot in test_status_data.snapshots.items():
        _save_snapshot(conn, test_status_data.owner_org, test_status_data.repo, branch, snapshot)
        logr.info(
            f"Saved snapshot for {test_status_data.owner_org}/{test_status_data.repo} "
            f"branch {branch}"
        )


def take_snapshot(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    branches: set[str],
    workflow_filter: str | set[str] | None = None,
    github_token: str | None = None,
):
    r"""
    Convenience function to take test status snapshots and save them in one call.
    
    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    branches - set of branch names to check (e.g., {'main', 'develop'})
    workflow_filter - a filter to match workflow paths. Either
        * a regex pattern string,  If a pattern is provided, only first matching workflow
          is returned. The default is (?:^|[\s_-])tests?(?:[\s_-]|$)
        * a set of exact workflow names to track.
    github_token - optional GitHub personal access token for higher rate limits
    """
    
    logr = logging.getLogger(__name__)
    
    test_status_data = get_test_status(owner_org, repo, branches, workflow_filter, github_token)
    
    if test_status_data.snapshots:
        save_test_status(conn, test_status_data)
        logr.info(
            f"Saved {len(test_status_data.snapshots)} snapshot(s) for "
            f"{owner_org}/{repo}"
        )
    else:
        logr.warning(f"No snapshots to save for {owner_org}/{repo}")
