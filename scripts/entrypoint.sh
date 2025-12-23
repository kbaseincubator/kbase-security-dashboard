#!/bin/bash

export KB_DEPLOYMENT_CONFIG="security_db_config.toml"

jinja $KB_DEPLOYMENT_CONFIG.jinja -X "^SECDB_" > $KB_DEPLOYMENT_CONFIG

# Use SECDB_PORT if set, otherwise default to 5000
PORT=${SECDB_PORT:-5000}

# FastAPI recommends running a single process service per docker container instance as below,
# and scaling via adding more containers. If we need to run multiple processes, use guvicorn as
# a process manager as described in the FastAPI docs
# https://fastapi.tiangolo.com/deployment/docker/#replication-number-of-processes

# exec so that tini properly forwards signals directly to uvicorn without bash getting its
# greasy mitts in the way
exec uvicorn --host 0.0.0.0 --port "$PORT" --factory kbase.security_dashboard:create_app
