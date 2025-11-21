"""
Run the data loader. Takes one argument, the path to the config file.
"""
import logging
from pathlib import Path
import psycopg2
import sys
import tomllib
from kbase._security_dashboard.load_all import process_repos


def _load_config(config_path: Path) -> dict:
    """Load configuration from TOML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _get_db_connection(config: dict) -> psycopg2.extensions.connection:
    """Create PostgreSQL connection from config."""
    pg_config = config["postgres"]
    return psycopg2.connect(
        host=pg_config["host"],
        database=pg_config["database"],
        user=pg_config["user"],
        password=pg_config["password"],
        port=pg_config.get("port", 5432)
    )


def main():
    logging.basicConfig(level=logging.INFO)
    logr = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logr.info(f"Loading configuration from {sys.argv[1]}")
        config = _load_config(Path(sys.argv[1]))
        
        # Connect to database
        logr.info("Connecting to PostgreSQL...")
        conn = _get_db_connection(config)
        
        # Process repositories
        process_repos(conn, config["github"]["token"], config["repos"])
        
        # Close connection
        conn.close()
        logr.info("Database connection closed")
        
        return 0
        
    except Exception as e:
        logr.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
