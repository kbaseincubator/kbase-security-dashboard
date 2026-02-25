"""
Run the data loader. Takes one argument, the path to the config file.
"""
import logging
from pathlib import Path

from kbase._security_dashboard.load_all import process_repos
from kbase._security_dashboard.util import get_db_connection, load_config


def run_repo_stats(config_path: Path) -> int:
    """
    Extract repo stats from codecov and github based on a configuration.
    
    config_path - the path to the config file.
    
    returns an exit code.
    """
    logging.basicConfig(level=logging.INFO)
    logr = logging.getLogger(__name__)
    
    conn = None
    try:
        # Load configuration
        logr.info(f"Loading configuration from {config_path}")
        config = load_config(config_path)
        
        # Connect to database
        logr.info("Connecting to PostgreSQL...")
        conn = get_db_connection(config)
        
        # Process repositories
        process_repos(conn, config["github"]["token"], config["repos"])
        return 0
        
    except Exception as e:
        logr.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        if conn:
            conn.close()
            logr.info("Database connection closed")
