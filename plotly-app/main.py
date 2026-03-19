import os
import waitress
from app import app

port = int(os.environ.get("PORT", 8050))

print(f"Starting server on port {port}...")

waitress.serve(app.server, host="0.0.0.0", port=port)
