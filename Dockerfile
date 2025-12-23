FROM python:3.13 AS build

# Write the git commit for the service
WORKDIR /git
COPY .git /git
RUN GITCOMMIT=$(git rev-parse HEAD) && echo "GIT_COMMIT=\"$GITCOMMIT\"" > /git/git_commit.py

FROM python:3.13

# libpw-dev is required for psycopg2
RUN apt update \
    && apt install -y tini libpq-dev \
    && rm -rf /var/lib/apt/lists/* 

# install uv
RUN pip install --upgrade pip && pip install uv	

# install deps
ARG UV_DEV_ARGUMENT=--no-dev
RUN mkdir /uvinstall
WORKDIR /uvinstall
COPY pyproject.toml uv.lock .python-version .
ENV UV_PROJECT_ENVIRONMENT=/usr/local/
RUN uv sync --locked --inexact $UV_DEV_ARGUMENT

# install the actual code
RUN mkdir /sdb
COPY src /sdb/
COPY scripts/* /sdb
COPY security_db_config.toml.jinja /sdb

COPY --from=build /git/git_commit.py /sdb/kbase/_security_dashboard/

WORKDIR /sdb

ENTRYPOINT ["tini", "--", "/sdb/entrypoint.sh"]
