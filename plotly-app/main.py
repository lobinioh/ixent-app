from app import app
import os
import waitress

port = int(os.environ.get("PORT", 8050))

waitress.serve(app, host="0.0.0.0", port=port)