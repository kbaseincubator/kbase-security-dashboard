"""
General utilities - get a postgres connection, load the configuration.
"""

from pathlib import Path
import psycopg2
import tomllib
from typing import Any


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from TOML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_db_connection(config: dict) -> psycopg2.extensions.connection:
    """Create PostgreSQL connection from the config provided by load_config."""
    pg_config = config["postgres"]
    return psycopg2.connect(
        host=pg_config["host"],
        database=pg_config["database"],
        user=pg_config["user"],
        password=pg_config["password"],
        port=pg_config.get("port", 5432)
    )
