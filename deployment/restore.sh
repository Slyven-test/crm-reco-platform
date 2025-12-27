#!/bin/bash

###############################################################################
# CRM Recommendation Platform - Restore Script
# 
# Usage: sudo bash restore.sh <backup_timestamp>
# Example: sudo bash restore.sh 20251227_143000
###############################################################################

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20251227_143000"
    echo ""
    echo "Available backups:"
    ls -1 /opt/crm-reco-platform/backups/db_*.sql.gz | sed 's/.*db_//' | sed 's/.sql.gz//'
    exit 1
fi

TIMESTAMP=$1
APP_DIR="/opt/crm-reco-platform"
BACKUP_DIR="${APP_DIR}/backups"
DB_NAME="crm_reco_db"
DB_USER="crm_reco_user"

echo "========================================"
echo "Restoring backup from ${TIMESTAMP}"
echo "========================================"
echo ""

# Check if backup exists
if [ ! -f "${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz" ]; then
    echo "Error: Backup not found: ${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"
    exit 1
fi

read -p "WARNING: This will overwrite current data. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "[1/3] Stopping application..."
systemctl stop crm-reco-platform

echo "[2/3] Restoring database..."
sudo -u postgres dropdb ${DB_NAME}
sudo -u postgres createdb ${DB_NAME}
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
gunzip -c ${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz | sudo -u postgres psql ${DB_NAME}

echo "[3/3] Restoring configuration..."
if [ -f "${BACKUP_DIR}/env_${TIMESTAMP}.backup" ]; then
    cp ${BACKUP_DIR}/env_${TIMESTAMP}.backup ${APP_DIR}/.env
    chmod 600 ${APP_DIR}/.env
    chown www-data:www-data ${APP_DIR}/.env
fi

echo "Starting application..."
systemctl start crm-reco-platform

echo ""
echo "========================================"
echo "Restore complete!"
echo "========================================"
echo ""
systemctl status crm-reco-platform --no-pager
