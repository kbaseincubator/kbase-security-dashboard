"""
Load Trivy scan data into postgres.
"""

import datetime
import logging
import psycopg2

from kbase._security_dashboard.trivy import TrivySnapshot


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the trivy_scans table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trivy_scans (
                org_user       VARCHAR(255) NOT NULL,
                repo           VARCHAR(255) NOT NULL,
                branch         VARCHAR(255) NOT NULL,
                timestamp      TIMESTAMPTZ NOT NULL,
                image_tags     TEXT[] NOT NULL,
                critical       INTEGER NOT NULL,
                high           INTEGER NOT NULL,
                medium         INTEGER NOT NULL,
                low            INTEGER NOT NULL,
                PRIMARY KEY (org_user, repo, branch, timestamp)
            )
        """)

        # Create index for time-series queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_trivy_scans_date
                ON trivy_scans (org_user, repo, branch, timestamp DESC)
        """)

        conn.commit()


def save_snapshot(
    conn: psycopg2.extensions.connection,
    snapshot: TrivySnapshot,
    snapshot_date: datetime.datetime,
):
    """
    Insert a Trivy scan snapshot into the table.

    Does nothing on conflict (same repo/branch/snapshot_date already exists).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO trivy_scans
                (org_user, repo, branch, timestamp, image_tags, critical, high, medium, low)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_user, repo, branch, timestamp) DO NOTHING
            """,
            (
                snapshot.owner_org,
                snapshot.repo,
                snapshot.branch,
                snapshot_date,
                snapshot.image_tags,
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
    Take Trivy scan snapshots for a repo's container images and save them.

    Scans container images for each branch. If a branch doesn't have a container image,
    it's skipped silently.

    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    branches - set of branch names to scan (e.g., {"main", "develop"})
    snapshot_date - the timestamp to use for this snapshot
    github_token - GitHub personal access token with read:packages scope.
        Note this must be a classic token to access repos you don't own.

    Raises exceptions if scans fail.
    """
    from kbase._security_dashboard.trivy import get_trivy_snapshot

    logr = logging.getLogger(__name__)

    for branch in branches:
        snapshot = get_trivy_snapshot(owner_org, repo, branch, github_token)

        if snapshot:
            save_snapshot(conn, snapshot, snapshot_date)
            logr.info(
                f"Saved Trivy snapshot for {owner_org}/{repo} "
                f"({branch}, tags={snapshot.image_tags})"
            )
        else:
            logr.debug(
                f"No container image to scan for {owner_org}/{repo} ({branch})"
            )
