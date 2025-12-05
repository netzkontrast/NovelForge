"""
This module initializes the database session and exports the Project model.
"""
from .session import get_session, engine
from .models import Project
