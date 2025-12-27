# Gunicorn Configuration for CRM Recommendation Platform
# Place in: /opt/crm-reco-platform/deployment/gunicorn.conf.py

import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 60
keepalive = 5

# Logging
accesslog = "/var/log/gunicorn/crm-reco-platform_access.log"
errorlog = "/var/log/gunicorn/crm-reco-platform_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "crm-reco-platform"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/crm-reco-platform.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = "/tmp"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
