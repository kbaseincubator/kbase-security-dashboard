"""
Load Code Scanning alerts data into postgres.
"""

import datetime
import logging
import psycopg2

from kbase._security_dashboard.code_scanning_alerts import CodeScanningAlertsSnapshot


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the code_scanning_alerts table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_scanning_alerts (
                org_user       VARCHAR(255) NOT NULL,
                repo           VARCHAR(255) NOT NULL,
                branch         VARCHAR(255) NOT NULL,
                timestamp      TIMESTAMPTZ NOT NULL,
                critical       INTEGER NOT NULL,
                high           INTEGER NOT NULL,
                medium         INTEGER NOT NULL,
                low            INTEGER NOT NULL,
                PRIMARY KEY (org_user, repo, branch, timestamp)
            )
        """)

        # Create index for time-series queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_scanning_alerts_date
                ON code_scanning_alerts (org_user, repo, branch, timestamp DESC)
        """)

        conn.commit()


def save_snapshot(
    conn: psycopg2.extensions.connection,
    snapshot: CodeScanningAlertsSnapshot,
    snapshot_date: datetime.datetime,
):
    """
    Insert a Code Scanning alerts snapshot into the table.

    Does nothing on conflict (same repo/branch/snapshot_date already exists).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO code_scanning_alerts
                (org_user, repo, branch, timestamp, critical, high, medium, low)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_user, repo, branch, timestamp) DO NOTHING
            """,
            (
                snapshot.owner_org,
                snapshot.repo,
                snapshot.branch,
                snapshot_date,
                snapshot.critical,
                snapshot.high,
                snapshot.medium,
                snapshot.low,
            )
        )
        conn.commit()


def take_snapshot(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    branches: set[str],
    snapshot_date: datetime.datetime,
    github_token: str,
):
    """
    Take Code Scanning alerts snapshots for a repo's branches and save them.

    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    branches - set of branch names to check (e.g., {"main", "develop"})
    snapshot_date - the timestamp to use for this snapshot
    github_token - GitHub personal access token. Note this must
        be a classic token to access repos you don't own

    Raises exceptions if API calls fail.
    """
    from kbase._security_dashboard.code_scanning_alerts import get_code_scanning_alerts_snapshot

    logr = logging.getLogger(__name__)

    for branch in branches:
        snapshot = get_code_scanning_alerts_snapshot(owner_org, repo, branch, github_token)
        save_snapshot(conn, snapshot, snapshot_date)
        logr.info(
            f"Saved Code Scanning alerts snapshot for {owner_org}/{repo} ({branch})"
        )
