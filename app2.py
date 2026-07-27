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


if __name__ == "__main__":
    # Run the application in debug mode
    app.run(host="0.0.0.0",port=5001, debug=True)
