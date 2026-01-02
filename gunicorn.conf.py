# Gunicorn configuration for production

import multiprocessing

# Bind to all interfaces on port 8000
bind = "0.0.0.0:8000"

# Number of worker processes
# Rule of thumb: 2 * CPU cores + 1
# For a small app with 2 users, 2 workers is sufficient
workers = 2

# Worker class
worker_class = "sync"

# Timeout for worker processes
timeout = 30

# Keep-alive connections
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Preload app for faster worker startup
preload_app = True

# Limit request line size
limit_request_line = 4094

# Limit request fields
limit_request_fields = 100
