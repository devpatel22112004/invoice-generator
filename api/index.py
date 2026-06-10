"""
Vercel serverless entry point for the Invoice Generator Flask app.

Vercel runs Python files under api/ as WSGI handlers. We import the Flask
app from the repo root (app.py) and expose it as the ASGI/WSGI handler.

Note: Vercel's filesystem is read-only except for /tmp, so we keep all
PDF generation in-memory (which the original app.py already does via
BytesIO), so no changes are required in app.py itself.
"""
import os
import sys

# Add the repo root to sys.path so `import app` resolves the original app.py
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Vercel's Python runtime looks for a module-level `app` (WSGI) or `handler`
# (ASGI). app.py exposes a Flask instance named `app`, so we just re-export it.
from app import app  # noqa: E402
