from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
import datetime
import logging
import psycopg2

from kbase._security_dashboard.service.timestamp import utcdatetime
from kbase._security_dashboard.load_all import process_repos
import traceback


_JOB_ID = "repoETL"


@dataclass
class ETLResult:
    time_complete: datetime.datetime  | None = None
    """ The time the ETL process completed or None if the process has not yet been run. """
    exception: None | str = None
    """ The exception that occurred or None if the process was successful. """ 


class RepoETLScheduler:
    """
    Schedules ETL from codecov and github into postgres.
    """

    def __init__(
        self,
        cron_string: str,
        github_token: str,
        repos: list[dict[str, str | list[str]]],
        postgres_host: str,
        postgres_port: int,
        postgres_database: str,
        postgres_user: str | None = None,
        postgres_password: str | None = None,
    ):
        """
        Initialize the scheduler.
        
        cron_string - a unix crontab string with the standard 5 elements.
        github_token - a GitHub personal access token. Note this must
            be a classic token to access repos you don't own
        repos - a list of repos. Each repo has the following keys:
            org - the github organization.
            repo  - the repo name.
            main_branch - the main branch name. Defaults to "main" if not present.
            dev_branch - the develop branch name. Defaults to "develop" if not present.
            test_workflows - a string or list of strings specifying which github action(s)
            are tests.
        postgres* fields are standard postgres creation inputs.
        """
        self._github_token = github_token
        self._repos = repos
        self.result = ETLResult()
        self._logr = logging.getLogger(__name__)
        self._pg_host = postgres_host
        self._pg_db = postgres_database
        self._pg_user = postgres_user
        self._pg_pwd = postgres_password
        self._pg_port = postgres_port
        # test connection
        self._get_connection()
        # Worked on a job store so the service can run the job immediately after coming up
        # if needed but since the db connection isn't pickleable and all fn arguments are
        # stored in the DB, including the password, decided not to bother for now.
        # It's doable, but not enough of a big deal to spend more time on it.

        # Initialize scheduler
        self._scheduler = AsyncIOScheduler(
            executors={
                "default": ThreadPoolExecutor(5), 
                "processpool": ProcessPoolExecutor(2), 
            },
            timezone=datetime.timezone.utc,
        )

        # Add periodic cron job, replacing if redeployed/restarted
        self._scheduler.add_job(
            self._run,
            trigger=CronTrigger.from_crontab(cron_string, timezone=datetime.timezone.utc),
            max_instances=1,
            coalesce=True,
            replace_existing=True,
            id=_JOB_ID,
        )

        self._scheduler.start()
        self._logr.info(f"Started scheduler with cron string: {cron_string}")

    def _get_connection(self):
        return psycopg2.connect(
            host=self._pg_host,
            database=self._pg_db,
            user=self._pg_user,
            password=self._pg_pwd,
            port=self._pg_port or 5432,
        )

    def _run(self):
        self._logr.info("Running ETL process in scheduler")
        err = None
        try:
            process_repos(self._get_connection(), self._github_token, self._repos)
        except Exception as e:
            self._logr.exception(f"ETL process failed: {e}")
            err = traceback.format_exc()
        self.result = ETLResult(time_complete=utcdatetime(), exception=err)
            

    def run_now(self):
        """
        Enqueue an immediate run if the the job is not currently running.
        """
        # Schedule immediate run using a DateTrigger with unique ID
        self._scheduler.add_job(
            self._run,
            trigger=DateTrigger(run_date=utcdatetime(), timezone=datetime.timezone.utc),
            max_instances=1,
            coalesce=True,
            replace_existing=False,
            id=_JOB_ID,
        )

    def close(self):
        """Shutdown the scheduler."""
        self._scheduler.shutdown(wait=True)
