FROM python:3.13 AS build

# Write the git commit for the service
WORKDIR /git
COPY .git /git
RUN GITCOMMIT=$(git rev-parse HEAD) && echo "GIT_COMMIT=\"$GITCOMMIT\"" > /git/git_commit.py

FROM python:3.13

ENV TRIVY_VER=0.69.1
ENV TRIVY_SHA=866c525bb6ff5d7b89da626e56e5e72019d7bcda8043cbb8324515b54ae0a411

# libpq-dev is required for psycopg2
# Install Trivy for container scanning
WORKDIR /opt
RUN TRIVY_FILE=trivy_${TRIVY_VER}_Linux-64bit.deb \
    && apt update \
    && apt install -y tini libpq-dev \
    && wget https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VER}/${TRIVY_FILE} \
    && echo "$TRIVY_SHA  ${TRIVY_FILE}" | sha256sum --check \
    && dpkg -i ${TRIVY_FILE} \
    && rm ${TRIVY_FILE} \
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
