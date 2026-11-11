"""Feature modules. Each module lives in its own folder with:

- models.py  : database tables (SQLAlchemy classes)
- schemas.py : request/response shapes (Pydantic classes)
- service.py : business logic and database work
- routes.py  : API endpoints (thin: validate input, call service, return output)

A module only has the files it needs (``health`` has no table, so no models.py).
"""
