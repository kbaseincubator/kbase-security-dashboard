"""
Load codecov data into postgres.
"""

import datetime
import logging
import psycopg2
from psycopg2.extras import execute_values

from kbase._security_dashboard.codecov import CoverageData, get_coverage_history


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the coverage table.
    """
    with conn.cursor() as cur:
        # Probably should make the tables configurable? Maybe not
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coverage_history (
                org_user      VARCHAR(255) NOT NULL,
                repo          VARCHAR(255) NOT NULL,
                branch        VARCHAR(255) NOT NULL,
                commit        CHAR(40) NOT NULL,
                timestamp     TIMESTAMPTZ NOT NULL,
                coverage      NUMERIC(5,2) NOT NULL,
                PRIMARY KEY (org_user, repo, branch, commit)
            )
        """)
        
        # Create index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_timestamp
                ON coverage_history (org_user, repo, branch, timestamp)
        """)
        
        conn.commit()


def save_coverage(
    conn: psycopg2.extensions.connection,
    coverage_data: CoverageData,
):
    """
    Insert coverage data into the table.
    Ignores rows that would violate the unique key.
    """
    rows = []
    for branch, commits in coverage_data.coverage.items():
        for c in commits:
            rows.append((
                coverage_data.owner_org,
                coverage_data.repo,
                branch,
                c.commit_id,
                c.timestamp,
                c.coverage
            ))
    
    if not rows:
        return

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO coverage_history (org_user, repo, branch, commit, timestamp, coverage)
            VALUES %s
            ON CONFLICT (org_user, repo, branch, commit) DO NOTHING
            """,
            rows
        )
        conn.commit()


def _get_last_sync_timestamp(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    branches: set[str] | None = None,
) -> datetime.datetime | None:
    """
    Get the most recent timestamp from the coverage_history table for the given repo.
    If branches are specified, only considers those branches.
    
    Returns None if no data exists for the repo.
    """
    with conn.cursor() as cur:
        if branches:
            cur.execute(
                """
                SELECT MAX(timestamp)
                FROM coverage_history
                WHERE org_user = %s AND repo = %s AND branch = ANY(%s)
                """,
                (owner_org, repo, list(branches))
            )
        else:
            cur.execute(
                """
                SELECT MAX(timestamp)
                FROM coverage_history
                WHERE org_user = %s AND repo = %s
                """,
                (owner_org, repo)
            )
        result = cur.fetchone()
        return result[0] if result and result[0] else None


def sync_coverage_data(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    branches: set[str] | None = None,
    force_full_sync: bool = False,
):
    """
    Pull codecov data and save it to postgres.
    
    Automatically determines the 'since' parameter based on the most recent
    data in the database. If no data exists, pulls all history.
    
    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    branches - only sync data for the given branches (None = all branches)
    force_full_sync - if True, ignores existing data and pulls full history
    """
    logr = logging.getLogger(__name__)
    
    # Determine starting point
    since = None
    if not force_full_sync:
        since = _get_last_sync_timestamp(conn, owner_org, repo, branches)
        if since:
            logr.info(f"Found existing data for {owner_org}/{repo}, syncing since {since}")
        else:
            logr.info(f"No existing data for {owner_org}/{repo}, pulling full history")
    else:
        logr.info(f"Force full sync requested for {owner_org}/{repo}")
    
    # Fetch coverage data
    coverage_data = get_coverage_history(
        owner_or_org=owner_org,
        repo=repo,
        branches=branches,
        since=since
    )
    
    # Save to database
    total_commits = sum(len(commits) for commits in coverage_data.coverage.values())
    logr.info(f"Saving {total_commits} commits across {len(coverage_data.coverage)} branches")
    save_coverage(conn, coverage_data)
    
    logr.info(f"Sync complete for {owner_org}/{repo}")
