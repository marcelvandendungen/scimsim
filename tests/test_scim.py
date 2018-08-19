import pytest
import scimsim

@pytest.fixture
def client():
    return scimsim.create_client()

def test_empty_db(client):
    """Retrieve something"""
    response = client.get('/')
    assert b'hello' in response.data
