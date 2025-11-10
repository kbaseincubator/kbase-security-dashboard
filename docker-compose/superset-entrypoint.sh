#!/bin/bash
set -e

echo
echo "*** Upgrading the superset metadata DB ***"
superset db upgrade

echo
echo "*** Creating superset admin user ***"
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname "${SUPERSET_ADMIN_FIRST_NAME:-Admin}" \
  --lastname "${SUPERSET_ADMIN_LAST_NAME:-User}" \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@example.com}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true

echo
echo "*** Initializing superset ***"
superset init

echo
echo "*** Running superset ***"
exec superset run -h 0.0.0.0 -p 8088 --with-threads
