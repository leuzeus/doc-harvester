"""SQLAdmin configuration for the Doc Harvester admin interface."""

# Third-party imports
from fastapi import FastAPI
from sqladmin import Admin, ModelView

# Local application imports
from models import Source, engine


# --------------------------------------------------------------------------------------
# Admin views
# --------------------------------------------------------------------------------------
class SourceAdmin(ModelView, model=Source):
    """Admin view providing CRUD management for sources."""

    column_list = [Source.id, Source.name, Source.kind, Source.enabled]
    column_searchable_list = [Source.name, Source.kind]
    form_columns = [Source.name, Source.kind, Source.url, Source.enabled, Source.extra]


# --------------------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------------------
def create_admin(app: FastAPI) -> Admin:
    """Attach the SQLAdmin dashboard to the provided FastAPI application."""

    admin = Admin(app=app, engine=engine)
    admin.add_view(SourceAdmin)
    return admin

