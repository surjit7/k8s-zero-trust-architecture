from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# Tell Flask it is behind one trusted proxy (your Ingress Controller)
# x_for=1 tells it to trust the first IP in the X-Forwarded-For header
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route('/')
def hello():
    # Because of ProxyFix, remote_addr now contains the real client IP!
    client_ip = request.remote_addr
    return f"Hello from Dockerized Flask! Your real IP is: {client_ip}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
