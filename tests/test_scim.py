from dateutil.parser import parse
import json
import pytest
import scimsim

@pytest.fixture
def client():
    scimsim.clear_data()
    return scimsim.create_client()


def test_not_found_response_in_json(client):
    """
        Check that any get of non-existing resources responds with proper SCIM error
    """
    response = client.get('/')
    assert response.status_code == 404
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "Not found"


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


def test_get_user_returns_not_found_when_user_does_not_exist(client):
    """
        Check that GET /Users/<id> responds with 404 Not Found when user does not exist
    """
    response = client.get('/scim/v2/users/100')
    assert response.status_code == 404


def test_get_user_returns_ok_when_user_returned(client):
    """
        Check that GET /Users/<id> responds with 200 OK when user is returned
    """
    d = {'userName': 'username'}
    response = client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')
    response = client.get('/scim/v2/users/' + str(response.json['id']))
    assert response.status_code == 200
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in response.json["schemas"]
    assert response.json["userName"] == d['userName']


def test_list_users_returns_ok(client):
    """
        Check that GET /Users responds with 200 OK
    """
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username1'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username2'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username3'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username4'}), content_type='application/json')

    response = client.get('/scim/v2/users')
    assert response.status_code == 200
    assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in response.json["schemas"]


def test_list_users_with_username_filter(client):
    """
        Check that GET /Users?filter=userName eq "username2" responds with 200 OK
    """
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username1'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username2'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username3'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username4'}), content_type='application/json')

    response = client.get('/scim/v2/users?filter=userName eq "username2"')
    assert response.status_code == 200
    assert len(response.json['Resources']) == 1
    assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in response.json["schemas"]


def test_list_users_with_pagination(client):
    """
        Check that GET /Users?startIndex=1&count=2 responds with correct list
    """
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username1'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username2'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username3'}), content_type='application/json')
    response = client.post('/scim/v2/users', data=json.dumps({'userName': 'username4'}), content_type='application/json')

    response = client.get('/scim/v2/users?startIndex=1&count=2')
    assert response.status_code == 200
    assert len(response.json['Resources']) == 2
    assert "urn:ietf:params:scim:api:messages:2.0:ListResponse" in response.json["schemas"]


def test_update_user_returns_ok(client):
    """
        Check that PUT /Users/id responds with 200 OK when successfully updating the user
    """
    d = {'userName': 'mvandend'}
    response = client.post('/scim/v2/users', data=json.dumps(d), content_type='application/json')

    d = response.json
    d['active'] = False

    response = client.put('/scim/v2/users/' + str(d['id']), data=json.dumps(d), content_type='application/json')

    assert response.status_code == 200
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in response.json["schemas"]
    assert response.json["userName"] == d['userName']
    assert response.json["active"] == False
    assert parse(response.json['meta']['created']) < parse(response.json['meta']['modified'])


def test_update_user_returns_not_found_when_user_does_not_exist(client):
    """
    """
    d = {'userName': 'mvandend'}

    response = client.put('/scim/v2/users/1', data=json.dumps(d), content_type='application/json')

    assert response.status_code == 404
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "user does not exist"


def test_create_group_returns_created(client):
    """
        Check that POST /Groups responds with 201 Created when successfully creating the user
    """
    d = {'displayName': 'groupname'}
    response = client.post('/scim/v2/groups', data=json.dumps(d), content_type='application/json')
    assert response.status_code == 201
    assert "urn:ietf:params:scim:schemas:core:2.0:Group" in response.json["schemas"]
    assert response.json["displayName"] == d['displayName']


def test_create_group_returns_bad_request_when_data_missing(client):
    """
        Check that POST /Groups responds with 400 Bad Request when data is missing from payload
    """
    response = client.post('/scim/v2/groups')
    assert response.status_code == 400
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "displayName is missing"


def test_create_group_returns_conflict_when_group_already_exists(client):
    """
        Check that POST /Groups responds with 409 Conflict when group to be created already exists
    """
    d = {'displayName': 'groupname'}
    client.post('/scim/v2/groups', data=json.dumps(d), content_type='application/json')
    response = client.post('/scim/v2/groups', data=json.dumps(d), content_type='application/json')
    assert response.status_code == 409
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "group already exists"


def test_delete_group_returns_not_found_if_group_does_not_exist(client):
    """
        Check that DELETE /Groups/<id> responds with 404 Not Found when user does not exist
    """
    response = client.delete('/scim/v2/groups/100')
    assert response.status_code == 404
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in response.json["schemas"]
    assert response.json["detail"] == "group not found"


def test_delete_group_returns_no_content_when_group_deleted_successfully(client):
    """
        Check that DELETE /Groups/<id> responds with 204 No Content when group was deleted
    """
    d = {'displayName': 'groupname'}
    response = client.post('/scim/v2/groups', data=json.dumps(d), content_type='application/json')
    response = client.delete('/scim/v2/groups/' + str(response.json['id']))
    assert response.status_code == 204


