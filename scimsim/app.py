#!/usr/local/bin/python3
import datetime 
import hashlib
import re
import urllib.parse
from flask import Flask, request, abort, jsonify, make_response, Response

app = Flask(__name__)

users = []
groups = []

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


@app.errorhandler(404)
def not_found(error):
    return make_scim_response(create_error_payload(404, 'Not found'), 404)


@app.route('/scim/v2/users', methods=['POST'])
def create_user():
    if not request.json or not 'userName' in request.json:
        scim_abort(400, 'userName is missing')

    alreadyExists = next((u for u in users if u['userName'] == request.json['userName']), None)
    if alreadyExists:
        scim_abort(409, 'user already exists')

    now = get_current_datetime()
    id = users[-1]['id'] + 1 if len(users) > 0 else 0
    user = {
        'schemas' : ['urn:ietf:params:scim:schemas:core:2.0:User'],
        'id': id,
        'userName': request.json['userName'],
        'externalId': request.json.get('externalId', ""),
        'active': True,
        'meta': {
            'resourceType': 'User',
            'created': now,
            'modified': now,
            'location': get_location('/scim/v2/users', id),
            'version': get_version(now, now)
        }
    }

    if 'name' in request.json:
        user['name'] = request.json['name']
        
    users.append(user)

    return make_scim_response(user, 201)


@app.route('/scim/v2/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):

    user = find_user(user_id)
    users.remove(user[0])

    return make_scim_response({}, 204)


@app.route('/scim/v2/users/<int:user_id>', methods=['GET'])
def get_user(user_id):

    user = find_user(user_id)

    return make_scim_response(user[0], 200)


@app.route('/scim/v2/users', methods=['GET'])
def list_users():

    startIndex = int(request.args.get('startIndex', 1)) - 1 # make zero based
    count = int(request.args.get('count', 10))
    filter = request.args.get('filter')

    filtered = get_filtered_users(filter)
    sliced = filtered[startIndex : startIndex + min(len(filtered), count)]
    mapped = list(map(lambda u: {'id': u['id'], 'userName': u['userName']}, sliced))

    response = {
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
        'totalResults': len(mapped),
        'Resources': mapped,
        'startIndex': 0,
        'itemsPerPage': 10
    }

    return make_scim_response(response, 200)


@app.route('/scim/v2/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = find_user(user_id)

    if not request.json or not 'userName' in request.json:
        scim_abort(400, 'userName is missing')

    user[0]['userName'] = request.json.get('userName', user[0]['userName'])
    user[0]['active'] = request.json.get('active', user[0]['active'])
    user[0]['meta']['modified'] = get_current_datetime()

    return make_scim_response(user[0], 200)


@app.route('/scim/v2/groups', methods=['POST'])
def create_group():
    id = groups[-1]['id'] + 1 if len(groups) > 0 else 0
    if not request.json or not 'displayName' in request.json:
        scim_abort(400, 'displayName is missing')

    alreadyExists = next((g for g in groups if g['displayName'] == request.json['displayName']), None)
    if alreadyExists:
        scim_abort(409, 'group already exists')

    now = get_current_datetime()
    group = {
        'id': id,
        'displayName': request.json['displayName'],
        'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'],
        'externalId': request.json.get('externalId', ""),
        'metadata': {
            'resourceType': 'Group'
            # TODO: add other attributes
        },
        'members': [],
        'version': get_version(now, now)
    }
    groups.append(group)
    return jsonify(group), 201


@app.route('/scim/v2/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):

    group = find_group(group_id)
    groups.remove(group[0])

    return make_scim_response({}, 204)


@app.route('/scim/v2/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):

    group = find_group(group_id)

    return make_scim_response(group[0], 200)


@app.route('/scim/v2/groups', methods=['GET'])
def get_groups():

    startIndex = int(request.args.get('startIndex', 1)) - 1 # make zero based
    count = int(request.args.get('count', 10))
    filter = request.args.get('filter')

    filtered = get_filtered_groups(filter)
    sliced = filtered[startIndex : startIndex + min(len(filtered), count)]
    mapped = list(map(lambda g: {'id': g['id'], 'displayName': g['displayName']}, sliced))

    response = {
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
        'totalResults': len(mapped),
        'Resources': mapped,
        'startIndex': startIndex,
        'itemsPerPage': count
    }
    return make_scim_response(response, 200)


@app.route('/scim/v2/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    group = find_group(group_id)
    if not request.json or not 'displayName' in request.json:
        scim_abort(400, 'displayName is missing')

    group[0]['displayName'] = request.json.get('displayName', group[0]['displayName'])

    return make_scim_response(group[0], 200)


@app.route('/scim/v2/groups/<int:group_id>', methods=['PATCH'])
def change_group(group_id):

    try:
        json = request.json
        operations = json['Operations']

        [patch(op, group_id) for op in operations]
        return make_scim_response(None, 204)

    except ValueError as ex:
        print(ex.args)
        scim_abort(400, 'unable to change membership', scim_type='invalidSyntax')
    except KeyError:
        return scim_abort(400, 'Invalid syntax', 'invalidSyntax')


def find_user(user_id):
    user = [user for user in users if user['id'] == user_id]
    if len(user) == 0:
        scim_abort(404, 'user does not exist')
    return user


def find_group(group_id):
    group = [group for group in groups if group['id'] == group_id]
    if len(group) == 0:
        scim_abort(404, 'group not found')
    return group

def patch(operation, group_id):

    if operation['op'] == 'add' and operation['path'] == 'members':
        [add_user(val, group_id) for val in operation['value']]
    elif operation['op'] == 'remove' and operation['path'].startswith('members'):
        # looks like: "path": 'members[value eq \"id\"]'
        name, val = get_member_to_remove(operation['path'])
        if name == 'value':
            remove_user(val, group_id)

    return operation


def add_user(value, group_id):
    print('adding user ' + value['value'] + ' to group ' + str(group_id))

    group = find_group(group_id)

    user = {'id':value['value'], '$ref': '/scim/v2/users/' + value['value']}
    group[0]['members'].append(user)


def remove_user(value, group_id):
    print('removing user ' + value + ' from group ' + str(group_id))
    group = find_group(group_id)
    group[0]['members'] = [m for m in group[0]['members'] if m['id'] != str(group_id)]


def get_member_to_remove(exp):

    if exp:
        m = re.match(r"^members\[(\w+)\s+eq\s+[\"'](\w+)[\"']\]$", exp)
        if m:
            attribute_name = m.groups()[0]
            attribute_value = m.groups()[1]
            return attribute_name, attribute_value

    raise ValueError('Invalid expression')


def make_scim_response(data, code):
    resp = make_response(jsonify(data))
    resp.headers['Content-Type'] = 'application/scim+json'
    return resp, code


def scim_abort(status, detail, scim_type=None):

    abort(make_response(jsonify(create_error_payload(status, detail, scim_type)), status))


def create_error_payload(status, detail, scim_type=None):
    data = {
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
        'status': str(status),
        'detail': detail
    }
    if scim_type:
        data['scimType'] = scim_type
    
    return data


def get_filtered_users(filter_exp):

    if filter_exp:
        m = re.match(r"^(\w+)\s+eq\s+[\"'](\w+)[\"']$", filter_exp)
        if m:
            attributeName = m.groups()[0]
            attributeValue = m.groups()[1]

            if attributeName not in ['userName', 'externalId']:
                scim_abort(400, 'only userName and externalId supported in filter', 'invalid_filter')

            return [u for u in users if u[attributeName] == attributeValue]

    return users


def get_filtered_groups(filter_exp):

    if filter_exp:
        m = re.match(r"^(\w+)\s+eq\s+[\"'](\w+)[\"']$", filter_exp)
        if m:
            attributeName = m.groups()[0]
            attributeValue = m.groups()[1]

            if attributeName not in ['displayName', 'externalId']:
                scim_abort(400, 'only displayName and externalId supported in filter', 'invalid_filter')

            return [g for g in groups if g[attributeName] == attributeValue]

    return groups


def get_current_datetime():
    d = datetime.datetime.utcnow()
    return d.isoformat("T") + "Z"


def get_version(created, modified):
    m = hashlib.md5()
    m.update(str(created).encode() + str(modified).encode())
    m.digest()
    return m.hexdigest()


def get_location(prefix, id):
    return urllib.parse.urljoin(prefix, str(id))


if __name__ == '__main__':
    app.run(debug=True)
