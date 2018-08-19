from .app import app

def create_client():
    return app.test_client()