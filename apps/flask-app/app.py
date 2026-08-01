import os
import logging
import sys
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
import redis

# Configure enterprise-grade structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Trust the internal ingress controller's X-Forwarded headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Retrieve configuration from environment variables (Zero-Trust/12-Factor App)
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis-0.redis-headless.default.svc.cluster.local')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

# Initialize Redis client
try:
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=2)
    logger.info(f"Initialized Redis client targeting {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    sys.exit(1)

@app.route('/')
def hello():
    client_ip = request.remote_addr
    logger.info(f"Received request at '/' from IP: {client_ip}")
    
    try:
        hits = cache.incr('hits')
        return f"Enterprise Flask API Online. Client IP: {client_ip}. Total Requests: {hits}.\n"
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis operation failed: {e}")
        return "Internal Service Error: Cache subsystem degraded.\n", 500

@app.route("/readyz")
def readyz():
    """Readiness probe endpoint for Kubernetes"""
    try:
        cache.ping()
        return "Service Ready", 200
    except redis.exceptions.ConnectionError:
        logger.warning("Readiness probe failed: Redis unavailable")
        return "Service Unavailable", 503

@app.route("/livez")
def livez():
    """Liveness probe endpoint for Kubernetes"""
    return "Service Alive", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
