#!/usr/local/bin/python3
from flask import Flask, request, abort, jsonify, make_response, Response

app = Flask(__name__)

users = []

@app.before_request
def log_request_info():
    print('\n>>> {} {} {}'.format(request.method, request.path, request.environ.get('SERVER_PROTOCOL')))
    print(*['\n>>> {}: {}'.format(x[0], x[1]) for x in request.headers ])
    print('\n>>> {}'.format(request.get_data()))


@app.after_request
def after(response):
    print('\n<<< {}'.format(response.status))
    print(*['\n<<< {}: {}'.format(x[0], x[1]) for x in response.headers ])
    print('\n<<< {}'.format(response.get_data()))

    return response


@app.route('/scim/v2/users', methods=['POST'])
def create_user():
    if not request.json or not 'userName' in request.json:
        scim_abort(400, 'userName is missing')

    alreadyExists = next((u for u in users if u['userName'] == request.json['userName']), None)
    if alreadyExists:
        scim_abort(409, 'user already exists')

    id = users[-1]['id'] + 1 if len(users) > 0 else 0
    user = {
        'schemas' : ['urn:ietf:params:scim:schemas:core:2.0:User'],
        'id': id,
        'userName': request.json['userName'],
        'externalId': request.json.get('externalId', ""),
        'active': True,
        'metadata': {
            'resourceType': 'User'
            # TODO: add other attributes
        }
    }

    if 'name' in request.json:
        user['name'] = request.json['name']
        
    users.append(user)

    return make_scim_response(user, 201)


@app.route('/scim/v2/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):

    user = [user for user in users if user['id'] == user_id]
    if len(user) == 0:
        scim_abort(404, 'user does not exist')

    users.remove(user[0])

    return make_scim_response({}, 204)


def make_scim_response(data, code):
    resp = make_response(jsonify(data))
    resp.headers['Content-Type'] = 'application/scim+json'
    return resp, code


def scim_abort(status, detail, scim_type=None):
    data = {
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
        'status': status,
        'detail': detail
    }
    if scim_type:
        data['scimType'] = scim_type

    abort(make_response(jsonify(data), status))


if __name__ == '__main__':
    app.run(debug=True)
