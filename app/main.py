import os
import waitress
from app import app

port = int(os.environ.get("PORT", 8050))
waitress.serve(app.server, host="0.0.0.0", port=port)