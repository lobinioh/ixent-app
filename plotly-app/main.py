import os
from app import app
from waitress import serve

server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    serve(server, host="0.0.0.0", port=port)
