#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
mkdir -p backups
file="backups/mysql-$(date -u +%Y%m%dT%H%M%SZ).sql"
trap 'rm -f "$file.partial"' EXIT
 docker compose --env-file .env.production -f compose.production.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u"$MYSQL_USER" --single-transaction --no-tablespaces "$MYSQL_DATABASE"' > "$file.partial"
test -s "$file.partial"
mv "$file.partial" "$file"
gzip "$file"
echo "$file.gz"
