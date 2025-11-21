"""
Load vulnerability snapshot data into postgres.
"""

import logging
import psycopg2

from kbase._security_dashboard.vulnerabilities import VulnerabilitySnapshot


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the vulnerability_snapshots table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vulnerability_snapshots (
                org_user       VARCHAR(255) NOT NULL,
                repo           VARCHAR(255) NOT NULL,
                timestamp  TIMESTAMPTZ NOT NULL,
                critical       INTEGER NOT NULL,
                high           INTEGER NOT NULL,
                medium         INTEGER NOT NULL,
                low            INTEGER NOT NULL,
                PRIMARY KEY (org_user, repo, timestamp)
            )
        """)
        
        # Create index for time-series queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_vulnerability_snapshots_date
                ON vulnerability_snapshots (org_user, repo, timestamp DESC)
        """)
        
        conn.commit()


def save_snapshot(
    conn: psycopg2.extensions.connection,
    snapshot: VulnerabilitySnapshot,
):
    """
    Insert a vulnerability snapshot into the table.
    
    Does nothing on conflict (same repo/snapshot_date already exists).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vulnerability_snapshots 
                (org_user, repo, timestamp, critical, high, medium, low)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_user, repo, timestamp) DO NOTHING
            """,
            (
                snapshot.owner_org,
                snapshot.repo,
                snapshot.snapshot_date,
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
    github_token: str,
):
    """
    Convenience function to take a vulnerability snapshot and save it in one call.
    
    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    github_token -     github_token - GitHub personal access token. Note this must
        be a classic token to access repos you don't own
    """
    from kbase._security_dashboard.vulnerabilities import get_vulnerability_snapshot
    
    logr = logging.getLogger(__name__)
    
    snapshot = get_vulnerability_snapshot(owner_org, repo, github_token)
    save_snapshot(conn, snapshot)
    logr.info(f"Saved vulnerability snapshot for {owner_org}/{repo}")
