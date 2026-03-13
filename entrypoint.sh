#!/bin/sh
set -e

export POSTGRES_DB="${POSTGRES_DB:-video_checker}"
export POSTGRES_USER="${POSTGRES_USER:-video_checker}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-video_checker}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_HOST="127.0.0.1"

PGDATA_DIR="/config/postgres"
mkdir -p "$PGDATA_DIR"

PG_BIN_DIR="$(find /usr/lib/postgresql -maxdepth 3 -type f -name initdb 2>/dev/null | sed 's#/initdb$##' | sort | tail -n 1)"
if [ -z "$PG_BIN_DIR" ]; then
  echo "PostgreSQL binaries not found under /usr/lib/postgresql"
  exit 1
fi

INITDB="$PG_BIN_DIR/initdb"
PG_CTL="$PG_BIN_DIR/pg_ctl"

if [ ! -s "$PGDATA_DIR/PG_VERSION" ]; then
  su - postgres -c "$INITDB -D '$PGDATA_DIR'"
  echo "host all all 127.0.0.1/32 md5" >> "$PGDATA_DIR/pg_hba.conf"
  su - postgres -c "$PG_CTL -D '$PGDATA_DIR' -o \"-c listen_addresses='127.0.0.1' -p $POSTGRES_PORT\" -w start"
  su - postgres -c "psql -h 127.0.0.1 -p $POSTGRES_PORT -d postgres -c \"ALTER USER postgres WITH PASSWORD '$POSTGRES_PASSWORD';\""
  su - postgres -c "psql -h 127.0.0.1 -p $POSTGRES_PORT -d postgres -c \"CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';\" || true"
  su - postgres -c "psql -h 127.0.0.1 -p $POSTGRES_PORT -d postgres -c \"CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;\" || true"
  su - postgres -c "$PG_CTL -D '$PGDATA_DIR' -m fast -w stop"
fi

su - postgres -c "$PG_CTL -D '$PGDATA_DIR' -o \"-c listen_addresses='127.0.0.1' -p $POSTGRES_PORT\" -w start"

exec uvicorn app.main:app --host 0.0.0.0 --port "${WEB_PORT:-8080}"
