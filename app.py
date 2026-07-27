from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
import redis

app = Flask(__name__)

# Tell Flask it is behind one trusted proxy (your Ingress Controller)
# x_for=1 tells it to trust the first IP in the X-Forwarded-For header
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Connect DIRECTLY to the Redis Pod using its Headless DNS name
cache = redis.Redis(host='redis-0.redis-headless.default.svc.cluster.local', port=6379)

@app.route('/')
def hello():
    # Because of ProxyFix, remote_addr now contains the real client IP!
    client_ip = request.remote_addr
    hits = cache.incr('hits')
    return f"Hello from GitOps Flask! Your real IP is: {client_ip}. You are visitor #{hits}."
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
