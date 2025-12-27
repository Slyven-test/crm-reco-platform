#!/bin/bash

###############################################################################
# CRM Recommendation Platform - Deployment Script
# 
# Usage: sudo bash deploy.sh
#
# This script:
# 1. Updates system packages
# 2. Installs dependencies (Python, PostgreSQL, Nginx)
# 3. Creates database and user
# 4. Sets up virtual environment
# 5. Installs Python packages
# 6. Configures services (Nginx, Gunicorn, Systemd)
# 7. Sets up SSL with Let's Encrypt
# 8. Starts services
###############################################################################

set -e  # Exit on error

# Configuration
APP_NAME="crm-reco-platform"
APP_DIR="/opt/${APP_NAME}"
APP_USER="www-data"
DB_NAME="crm_reco_db"
DB_USER="crm_reco_user"
DB_PASSWORD="$(openssl rand -base64 32)"
DOMAIN="your-domain.com"  # CHANGE THIS

echo "========================================"
echo "CRM Recommendation Platform Deployment"
echo "========================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (use sudo)"
   exit 1
fi

echo "[1/10] Updating system packages..."
apt-get update
apt-get upgrade -y

echo "[2/10] Installing system dependencies..."
apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    build-essential \
    libpq-dev

echo "[3/10] Creating application directory..."
mkdir -p ${APP_DIR}
mkdir -p ${APP_DIR}/logs
mkdir -p /var/log/gunicorn
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
chown -R ${APP_USER}:${APP_USER} /var/log/gunicorn

echo "[4/10] Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH ENCRYPTED PASSWORD '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
\q
EOF

echo "Database credentials:"
echo "  DB_NAME: ${DB_NAME}"
echo "  DB_USER: ${DB_USER}"
echo "  DB_PASSWORD: ${DB_PASSWORD}"
echo ""
echo "IMPORTANT: Save these credentials securely!"
echo ""

echo "[5/10] Cloning repository..."
cd /opt
if [ -d "${APP_NAME}/.git" ]; then
    echo "Repository already exists, pulling latest..."
    cd ${APP_NAME}
    sudo -u ${APP_USER} git pull
else
    sudo -u ${APP_USER} git clone https://github.com/Slyven-test/crm-reco-platform.git
    cd ${APP_NAME}
fi

echo "[6/10] Creating Python virtual environment..."
sudo -u ${APP_USER} python3.10 -m venv venv
sudo -u ${APP_USER} venv/bin/pip install --upgrade pip

echo "[7/10] Installing Python dependencies..."
sudo -u ${APP_USER} venv/bin/pip install -r deployment/requirements.txt

echo "[8/10] Creating .env file..."
cat > ${APP_DIR}/.env <<EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Database Configuration
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}

# Application Settings
DEBUG=False
TESTING=False

# Connectors Configuration
CONNECTORS_CONFIG_DIR=${APP_DIR}/config/connectors

# Logging
LOG_LEVEL=INFO
LOG_FILE=${APP_DIR}/logs/app.log
EOF

chown ${APP_USER}:${APP_USER} ${APP_DIR}/.env
chmod 600 ${APP_DIR}/.env

echo "[9/10] Configuring services..."

# Nginx
cp ${APP_DIR}/deployment/nginx.conf /etc/nginx/sites-available/${APP_NAME}
sed -i "s/your-domain.com/${DOMAIN}/g" /etc/nginx/sites-available/${APP_NAME}
ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Systemd service
cp ${APP_DIR}/deployment/systemd.service /etc/systemd/system/${APP_NAME}.service
systemctl daemon-reload
systemctl enable ${APP_NAME}

echo "[10/10] Setting up SSL with Let's Encrypt..."
echo "Note: Make sure your domain ${DOMAIN} points to this server's IP!"
read -p "Press Enter to continue with SSL setup (or Ctrl+C to skip)..."

certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN}

echo "Starting services..."
systemctl start ${APP_NAME}
systemctl restart nginx

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Application URL: https://${DOMAIN}"
echo ""
echo "Service status:"
systemctl status ${APP_NAME} --no-pager
echo ""
echo "Useful commands:"
echo "  - View logs: sudo journalctl -u ${APP_NAME} -f"
echo "  - Restart app: sudo systemctl restart ${APP_NAME}"
echo "  - Restart nginx: sudo systemctl restart nginx"
echo "  - Check status: sudo systemctl status ${APP_NAME}"
echo ""
echo "Database credentials saved in: ${APP_DIR}/.env"
echo ""
