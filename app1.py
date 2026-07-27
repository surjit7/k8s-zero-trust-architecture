from flask import Flask, make_response, request
import os
# Initialize the Flask application
app = Flask(__name__)


# Define the route for the root URL ("/")
@app.route("/")
def home():
    import time
    time.sleep(2)
    session_cookie = request.cookies.get("backend_session")
    response = make_response(
            f"Hello from app 1  Handled by PID: {os.getpid()}\n"
            )
    if not session_cookie:
        response.set_cookie("backend_session", "user_instance_A")
    return response


if __name__ == "__main__":
    # Run the application in debug mode
    app.run(port=5001, debug=True)
