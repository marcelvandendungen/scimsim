import json
import pytest
import scimsim

@pytest.fixture
def client():
    scimsim.clear_data()
    return scimsim.create_client()


def test_create_user_returns_created(client):
    """
        Check that POST /Users responds with 201 Created when successfully creating the user
    """
    d = {'userName': 'mvandend'}
    response = client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')
    assert response.status_code == 201
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in response.json["schemas"]
    assert response.json["userName"] == d['userName']
    assert response.json["active"] == True


def test_create_user_returns_bad_request_when_data_missing(client):
    """
        Check that POST /Users responds with 400 Bad Request when data is missing from payload
    """
    response = client.post('/scim/v2/users')
    assert response.status_code == 400
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "userName is missing"


def test_create_user_returns_conflict_when_user_already_exists(client):
    """
        Check that POST /Users responds with 409 Conflict when user to be created already exists
    """
    d = {'userName': 'username'}
    client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')
    assert response.status_code == 409
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "user already exists"


def test_delete_user_returns_not_found_if_user_does_not_exist(client):
    """
        Check that DELETE /Users/<id> responds with 404 Not Found when user does not exist
    """
    response = client.delete('/scim/v2/users/100')
    assert response.status_code == 404
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "user does not exist"


def test_delete_user_returns_no_content_when_user_deleted_successfully(client):
    """
        Check that DELETE /Users/<id> responds with 204 No Content when user was deleted
    """
    d = {'userName': 'username'}
    response = client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')
    response = client.delete('/scim/v2/users/' + str(response.json['id']))
    assert response.status_code == 204
