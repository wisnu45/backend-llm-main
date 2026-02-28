#!/usr/bin/env sh
set -eu

MIGRATIONS_DIR=${MIGRATIONS_DIR:-/app/schema/migrations}
WAIT_FOR_DB_MAX=${WAIT_FOR_DB_MAX:-30}
SLEEP_SECONDS=${SLEEP_SECONDS:-1}

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USERNAME=${DB_USERNAME:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_DATABASE=${DB_DATABASE:-postgres}

if ! command -v psql >/dev/null 2>&1; then
  echo "psql client is not available on PATH" >&2
  exit 1
fi

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Migration directory '$MIGRATIONS_DIR' does not exist" >&2
  exit 1
fi

export PGPASSWORD="${DB_PASSWORD}"

attempt=0
until psql --host "$DB_HOST" --port "$DB_PORT" --username "$DB_USERNAME" --dbname "$DB_DATABASE" --command "SELECT 1" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$WAIT_FOR_DB_MAX" ]; then
    echo "Database is still unavailable after ${WAIT_FOR_DB_MAX} attempts" >&2
    exit 1
  fi
  echo "Waiting for database connection... (${attempt}/${WAIT_FOR_DB_MAX})"
  sleep "$SLEEP_SECONDS"
done

echo "Database connection established"

OLD_IFS=$IFS
IFS='
'
migration_files=$(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name "*.sql" -print | sort)
IFS=$OLD_IFS

if [ -z "$migration_files" ]; then
  echo "No migrations found in $MIGRATIONS_DIR"
  exit 0
fi

IFS='
'
for file in $migration_files; do
  echo "Applying migration: $(basename "$file")"
  psql --host "$DB_HOST" --port "$DB_PORT" --username "$DB_USERNAME" --dbname "$DB_DATABASE" --set ON_ERROR_STOP=on --file "$file"
  echo "Migration completed: $(basename "$file")"
done
IFS=$OLD_IFS

echo "All migrations applied successfully"
