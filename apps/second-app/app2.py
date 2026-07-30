from flask import Flask, make_response, request
import os
# Initialize the Flask application
app = Flask(__name__)


# Define the route for the root URL ("/")
@app.route("/")
def home():
    return "Hello second app"
    import time
    time.sleep(2)
    session_cookie = request.cookies.get("backend_session")
    response = make_response(
            f"Hello from app 2  Handled by PID: {os.getpid()}\n"
            )
    if not session_cookie:
        response.set_cookie("backend_session", "user_instance_B")
    return response

@app.route("/readyz")
def readyz():
    return "OK", 200

@app.route("/livez")
def livez():
    return "OK", 200


if __name__ == "__main__":
    # 1. Read environment variables dynamically
    # Fallback to port 5001 if PORT env variable is not set
    port_env = int(os.environ.get("PORT", 5001))

    # Enable debug mode ONLY if APP_ENV is set to "development"
    is_debug = os.environ.get("APP_ENV", "production") == "development"

    app.run(host="0.0.0.0", port=port_env, debug=is_debug)