#!/bin/bash

###############################################################################
# CRM Recommendation Platform - Backup Script
# 
# Usage: bash backup.sh
#
# Cron: 0 2 * * * /opt/crm-reco-platform/deployment/backup.sh
###############################################################################

set -e

# Configuration
APP_DIR="/opt/crm-reco-platform"
BACKUP_DIR="${APP_DIR}/backups"
DB_NAME="crm_reco_db"
DB_USER="crm_reco_user"
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "[$(date)] Starting backup..."

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Database backup
echo "[$(date)] Backing up database..."
pg_dump -U ${DB_USER} ${DB_NAME} | gzip > ${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz

# Application files backup
echo "[$(date)] Backing up application files..."
tar -czf ${BACKUP_DIR}/app_${TIMESTAMP}.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='backups' \
    ${APP_DIR}

# Configuration backup
echo "[$(date)] Backing up configuration..."
cp ${APP_DIR}/.env ${BACKUP_DIR}/env_${TIMESTAMP}.backup

# Remove old backups
echo "[$(date)] Cleaning old backups (older than ${RETENTION_DAYS} days)..."
find ${BACKUP_DIR} -name "*.gz" -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR} -name "*.backup" -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete!"
echo "Backup location: ${BACKUP_DIR}"
ls -lh ${BACKUP_DIR}/*${TIMESTAMP}*
