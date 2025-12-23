#!/usr/bin/env python

"""
The entry point for the security dashboard loading service or CLI.

If run as a main script, performs a single load of codecov and GHA data into Postgres.
"""

import sys
from pathlib import Path
from kbase._security_dashboard.cli import run_repo_stats


if __name__ == "__main__":
    sys.exit(run_repo_stats(Path(sys.argv[1])))
