#!/bin/bash

###############################################################################
# CRM Recommendation Platform - Monitoring Dashboard
# 
# Usage: bash monitor.sh
###############################################################################

APP_NAME="crm-reco-platform"
APP_DIR="/opt/${APP_NAME}"

clear

echo "========================================"
echo "  CRM Recommendation Platform Monitor"
echo "========================================"
echo ""

echo "[System Information]"
echo "  Hostname: $(hostname)"
echo "  Uptime: $(uptime -p)"
echo "  Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

echo "[Service Status]"
echo "  Application:"
systemctl status ${APP_NAME} --no-pager | grep "Active:" | sed 's/^/    /'
echo "  Nginx:"
systemctl status nginx --no-pager | grep "Active:" | sed 's/^/    /'
echo "  PostgreSQL:"
systemctl status postgresql --no-pager | grep "Active:" | sed 's/^/    /'
echo ""

echo "[Resource Usage]"
echo "  CPU:"
top -bn1 | grep "Cpu(s)" | sed 's/^/    /'
echo "  Memory:"
free -h | grep "Mem:" | awk '{print "    Used: "$3" / "$2" ("int($3/$2*100)"%)"}'
echo "  Disk:"
df -h ${APP_DIR} | tail -1 | awk '{print "    Used: "$3" / "$2" ("$5")"}'
echo ""

echo "[Database]"
echo "  Connections:"
sudo -u postgres psql -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';" -t 2>/dev/null | sed 's/^/    /'
echo "  Database size:"
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('crm_reco_db'));" -t 2>/dev/null | sed 's/^/    /'
echo ""

echo "[Recent Logs - Last 10 entries]"
journalctl -u ${APP_NAME} -n 10 --no-pager | sed 's/^/  /'
echo ""

echo "[Network]"
echo "  Listening ports:"
ss -tulpn | grep -E ':(80|443|8000|5432)' | sed 's/^/    /'
echo ""

echo "[SSL Certificate]"
if [ -f "/etc/letsencrypt/live/your-domain.com/cert.pem" ]; then
    echo "  Expiry:"
    openssl x509 -enddate -noout -in /etc/letsencrypt/live/your-domain.com/cert.pem | sed 's/^/    /'
else
    echo "    No SSL certificate found"
fi
echo ""

echo "[Backup Status]"
echo "  Last backup:"
ls -lht ${APP_DIR}/backups/*.sql.gz 2>/dev/null | head -1 | awk '{print "    "$6" "$7" "$8" - "$9}'
echo "  Total backups:"
ls -1 ${APP_DIR}/backups/*.sql.gz 2>/dev/null | wc -l | sed 's/^/    /'
echo ""

echo "========================================"
echo "Press any key to refresh (Ctrl+C to exit)"
read -n 1 -s
exec $0
