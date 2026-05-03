import os
print("Current Working Directory:", os.getcwd())
from flask import Flask
from routes.auth_routes import auth_bp

app = Flask(__name__)
app.secret_key = "secret123"

# 🔒 Prevent browser caching
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)


