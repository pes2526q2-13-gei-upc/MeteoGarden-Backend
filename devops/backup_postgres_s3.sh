#!/bin/bash
set -e

cd /opt/meteogarden

set -a
source .postgres.env
set +a

BACKUP_DIR="/opt/meteogarden/backups"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="meteogarden_postgres_$DATE.sql.gz"
BUCKET="s3://meteogarden-postgres-backups/postgres"

mkdir -p "$BACKUP_DIR"

docker exec meteogarden_pg pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/$BACKUP_FILE"

aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "$BUCKET/$BACKUP_FILE"

find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +7 -delete