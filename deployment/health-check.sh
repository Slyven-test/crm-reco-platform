#!/bin/bash

###############################################################################
# CRM Recommendation Platform - Health Check Script
# 
# Usage: bash health-check.sh
#
# Cron: */5 * * * * /opt/crm-reco-platform/deployment/health-check.sh
###############################################################################

APP_NAME="crm-reco-platform"
HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/${APP_NAME}/health-check.log"
ALERT_EMAIL="admin@example.com"  # CHANGE THIS

# Create log dir if not exists
mkdir -p /var/log/${APP_NAME}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> ${LOG_FILE}
}

send_alert() {
    local subject="$1"
    local body="$2"
    echo "${body}" | mail -s "[${APP_NAME}] ${subject}" ${ALERT_EMAIL}
}

# Check if service is running
if ! systemctl is-active --quiet ${APP_NAME}; then
    log "ERROR: Service is not running!"
    send_alert "Service Down" "The ${APP_NAME} service is not running. Attempting restart..."
    systemctl restart ${APP_NAME}
    sleep 5
    
    if ! systemctl is-active --quiet ${APP_NAME}; then
        log "ERROR: Failed to restart service!"
        send_alert "Service Restart Failed" "Failed to restart ${APP_NAME} service. Manual intervention required."
        exit 1
    else
        log "INFO: Service restarted successfully"
        send_alert "Service Restarted" "${APP_NAME} service was down and has been restarted."
    fi
fi

# Check HTTP health endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${HEALTH_URL} || echo "000")

if [ "${HTTP_CODE}" != "200" ]; then
    log "ERROR: Health check failed (HTTP ${HTTP_CODE})"
    send_alert "Health Check Failed" "Health endpoint returned HTTP ${HTTP_CODE}. Service may be unhealthy."
    exit 1
fi

log "INFO: Health check passed (HTTP ${HTTP_CODE})"
exit 0
