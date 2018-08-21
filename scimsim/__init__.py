from .app import app
from .app import users
from .app import groups

def create_client():
    return app.test_client()

def clear_data():
    users.clear()
    groups.clear()
