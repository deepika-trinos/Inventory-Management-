"""Model registry.

Alembic compares the database with ``Base.metadata`` to write migrations. A
table is only part of ``Base.metadata`` after its ``models.py`` has been
imported, so every module's models are imported here.

When a slice adds a new module with tables, add one import line, e.g.:
    from app.modules.users import models as users_models  # noqa: F401

"""

from app.core.database import Base  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.audit import service as _audit_service  # noqa: F401  (switches on the append-only guard)
from app.modules.categories import models as categories_models  # noqa: F401
from app.modules.employees import models as employees_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
