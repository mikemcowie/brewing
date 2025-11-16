"""
Stub env.py file for brewing.db.migrate.

All the real migration machinery is in the migrate module,
but alembic requires this file as a script.

So migrations pushes all the required context into a contextvar,
leaving this as the bare minimum required env.py .
"""

from brewing.db.migrate import run

run()
